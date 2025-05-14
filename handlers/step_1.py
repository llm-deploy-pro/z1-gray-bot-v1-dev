import asyncio
import logging
import datetime # Retained for internal logging timestamps
import hashlib # For the placeholder generate_user_secure_id
from dataclasses import dataclass # For TimedMessage
from typing import List # For type hinting

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError # For more specific error handling

# --- 临时的 generate_user_secure_id 占位符 ---
def generate_user_secure_id(user_id_str: str) -> str:
    """Generates a placeholder secure ID."""
    return hashlib.md5(user_id_str.encode()).hexdigest()[:16]
# --- End of placeholder ---

logger = logging.getLogger(__name__)

# --- Callback Data Constants (保持不变) ---
CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN = "s1_initiate_diagnostic_scan"
CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW = "s1_view_protocol_overview"
CALLBACK_S1_IGNORE_WARNING = "s1_ignore_warning"
CALLBACK_S2_FROM_DIAGNOSTIC = "step2_entry_from_diagnostic"
CALLBACK_S2_FROM_PROTOCOL = "step2_entry_from_protocol"
CALLBACK_S2_FROM_IGNORE = "step2_entry_from_ignore"

# --- Flow State Constants (保持不变) ---
AWAITING_STEP_1_BUTTON = "AWAITING_STEP_1_BUTTON"
AWAITING_STEP_2_FROM_DIAGNOSTIC = "AWAITING_STEP_2_FROM_DIAGNOSTIC"
AWAITING_STEP_2_FROM_PROTOCOL = "AWAITING_STEP_2_FROM_PROTOCOL"
AWAITING_STEP_2_FROM_IGNORE = "AWAITING_STEP_2_FROM_IGNORE"
STEP_1_DIAGNOSTIC_RUNNING = "STEP_1_DIAGNOSTIC_RUNNING"
STEP_2_STARTED_ANALYSIS = "step_2_started_analysis"


@dataclass
class TimedMessage:
    text: str
    delay_before: float = 0.8 # Default delay before sending this message
    typing: bool = True


async def send_delayed_sequence(
    bot, 
    chat_id: int, 
    sequence: List[TimedMessage], 
    initial_delay: float = 0
) -> None:
    if initial_delay > 0:
        await asyncio.sleep(initial_delay)

    for item in sequence:
        delay_before_send = item.delay_before
        show_typing = item.typing
        text_to_send = item.text

        if show_typing and delay_before_send > 0.2: 
            try:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except TelegramError as e_chat_action:
                logger.warning(f"Failed to send chat action in chat {chat_id}: {e_chat_action}")
        
        if delay_before_send > 0:
            await asyncio.sleep(delay_before_send)
        
        try:
            await bot.send_message(
                chat_id=chat_id, 
                text=text_to_send, 
                parse_mode=ParseMode.HTML
            )
        except TelegramError as e_send: 
            logger.warning(f"Failed to send message in sequence to chat {chat_id}: '{item.text[:30]}...' due to {e_send}")
        except Exception as e_general: 
            logger.error(f"Unexpected error sending message in sequence to chat {chat_id}: '{item.text[:30]}...' due to {e_general}", exc_info=True)


async def send_system_error_reply(
    target_object: Update | None, 
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int | str = "Unknown",
    error_text: str = "An unexpected system error occurred. Please try the /start sequence again."
) -> None:
    logger.error(f"Sending system error reply to user {user_id}: {error_text}")
    try:
        reply_target = None
        # Prioritize replying to the original message context if available
        if target_object and hasattr(target_object, 'message') and target_object.message: # For CallbackQuery's query object
            reply_target = target_object.message
        elif target_object and hasattr(target_object, 'reply_html'): # For Update's message object
            reply_target = target_object
        
        if reply_target and hasattr(reply_target, 'reply_html'):
             await reply_target.reply_html(f"⚠️ <b>SYSTEM ERROR:</b>\n{error_text}")
        elif user_id != "Unknown" and context.bot: # Fallback if no direct reply object
            await context.bot.send_message(chat_id=user_id, text=f"⚠️ <b>SYSTEM ERROR:</b>\n{error_text}", parse_mode=ParseMode.HTML)
    except Exception as e_reply:
        logger.error(f"CRITICAL: Failed to send system error reply to user {user_id}: {e_reply}")


async def start_step_1_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        logger.warning("start_step_1_flow called without a message or effective_chat.")
        return
    
    user = update.effective_user
    if not user:
        logger.warning("Effective user is None in start_step_1_flow.")
        await send_system_error_reply(update.message, context, "UnknownUserOnInit", "User identification failed.")
        return

    user_id = user.id
    current_step = context.user_data.get("current_flow_step", "")
    entry_point_s2_stale = context.user_data.get("entry_point_s2", "")

    if update.message.text == "/start" and current_step.startswith("AWAITING_STEP_2_FROM_"):
        logger.warning(
            f"User {user_id} (State: {current_step}, Entry: {entry_point_s2_stale}) initiated /start while awaiting Step 2. "
            "Current recovery: Inform and restart Step 1."
        )
        await update.message.reply_html(
            "⚠️ <b>System State Inconsistency Detected.</b>\n"
            "Your previous session was awaiting entry into Step ②. "
            "For now, we will restart the initialization sequence."
        )
        context.user_data.pop("current_flow_step", None)
        context.user_data.pop("entry_point_s2", None)
        context.user_data.pop("risk_score", None) 
        logger.info(f"User {user_id} stale AWAITING_STEP_2 state cleared by /start. Proceeding with fresh Step 1.")

    logger.info(f"User {user_id} ({user.username or 'N/A'}) started step_1_flow. Current step before: {current_step}")
    secure_id = generate_user_secure_id(str(user_id))
    context.user_data["secure_id"] = secure_id

    try:
        # Initial Step 1 messages with their original pacing and direct replies
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(0.5)
        await update.message.reply_html("🔷 ACCESS NODE CONFIRMED\n→ PROTOCOL [Z1-GRAY_ΔPRIME] INITIALIZED")
        
        await asyncio.sleep(1.5) # Delay after first message
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(0.6) # Short typing delay
        message_text_2 = (
            f"🔹 SECURE IDENTIFIER GENERATED\n"
            f"→ USER_SECURE_ID: <code>{secure_id}</code>\n"
            f"→ AUTH_LAYER: 2B | SYNC_STATUS: PENDING"
        )
        await update.message.reply_html(message_text_2) 
        
        await asyncio.sleep(2.7) # Delay after second message
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(0.6)
        await update.message.reply_html(
            "⚠️ INITIAL NODE ANALYSIS: CRITICAL WARNING\n"
            "→ STABILITY RISK INDEX: 0.84 (ABOVE THRESHOLD)\n"
            "→ TRACE_SIGNAL: NON-STANDARD ALIGNMENT"
        )
        await asyncio.sleep(4.5)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(0.6)
        await update.message.reply_html(
            "🔒 SYSTEM ALERT: Your access node has entered a volatility state.\n"
            "→ Interruption may trigger node quarantine protocol."
        )
        await asyncio.sleep(3.2)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(0.6)
        await update.message.reply_html(
            "🧠 ACTION REQUIRED: Begin full TRACE_DIAGNOSTIC to determine node viability.\n"
            "→ Delayed response = elevated risk of deactivation"
        )
        await asyncio.sleep(2.8)

        keyboard = [
            [InlineKeyboardButton("🧪 RUN TRACE_DIAGNOSTIC NOW ⚡️", callback_data=CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN)],
            [InlineKeyboardButton("📄 VIEW SYSTEM PROTOCOL 📘", callback_data=CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW)],
            [InlineKeyboardButton("⛔️ IGNORE SYSTEM WARNING (NOT RECOMMENDED)", callback_data=CALLBACK_S1_IGNORE_WARNING)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(0.5)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="SELECT ACTION:", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        
        context.user_data["current_flow_step"] = AWAITING_STEP_1_BUTTON
        logger.info(f"User {user_id}: current_flow_step set to {AWAITING_STEP_1_BUTTON}.")
    except Exception as e:
        logger.error(f"Error in start_step_1_flow for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(update.message, context, user_id, "System communication error during initialization.")

# --- Callback Handlers (Applying new rhythm using send_delayed_sequence) ---

async def s1_initiate_diagnostic_scan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        if query: await query.answer()
        return
    
    user_id = user.id
    logger.info(f"BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN} at {datetime.datetime.utcnow().isoformat()}Z")
    
    await query.answer("Processing...")
    try:
        await query.edit_message_text(text="ACTION SELECTED: 🧪 RUN TRACE_DIAGNOSTIC NOW ⚡️", reply_markup=None)
        
        diagnostic_sequence = [
            TimedMessage(text="🔬 <b>TRACE_DIAGNOSTIC INITIATED...</b>\nAnalyzing node stability signatures...", delay_before=1.2),
            TimedMessage(text="🧠 Analyzing ΔPrime vector clusters...", delay_before=2.8),
            TimedMessage(text="📡 Signal drift detected... calibrating...", delay_before=2.4),
            TimedMessage(text="✅ <b>DIAGNOSTIC PHASE 1 COMPLETE.</b>", delay_before=1.8, typing=False), # Adjusted delay
            TimedMessage(text="<b>ALIGNMENT ANOMALIES DETECTED</b>\n\nYour node trace reveals core-misalignment clusters requiring deeper analysis.", delay_before=2.8), # Adjusted delay
            TimedMessage(text="🧠 <b>Proceed to Step ②: TRACE_REPORT_Δ7</b> for critical breakdown.", delay_before=2.0), # Adjusted delay
        ]
        await send_delayed_sequence(context.bot, query.message.chat_id, diagnostic_sequence, initial_delay=0.8)

        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.5) # Adjusted delay before final button
        keyboard_step2 = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ CONTINUE TO STEP ②", callback_data=CALLBACK_S2_FROM_DIAGNOSTIC)]])
        await context.bot.send_message(chat_id=query.message.chat_id, text="Ready to continue?", reply_markup=keyboard_step2, parse_mode=ParseMode.HTML)
        
        try:
            context.user_data["entry_point_s2"] = "from_diagnostic"
            context.user_data["current_flow_step"] = AWAITING_STEP_2_FROM_DIAGNOSTIC
            logger.info(f"User {user_id} completed diagnostic. Status set to: {AWAITING_STEP_2_FROM_DIAGNOSTIC}")
        except Exception as e_data_log:
            logger.error(f"Error setting user_data or logging after diagnostic for user {user_id}: {e_data_log}", exc_info=True)
            # Not sending user-facing error here, rely on main try-except if this is critical

    except Exception as e: 
        logger.error(f"Error in s1_initiate_diagnostic_scan_callback (main try block) for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(query, context, user_id, "An error occurred during diagnostic processing.")


async def s1_view_protocol_overview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        if query: await query.answer()
        return
        
    user_id = user.id
    logger.info(f"BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW} at {datetime.datetime.utcnow().isoformat()}Z")
    await query.answer()
    try:
        await query.edit_message_text(text="ACTION SELECTED: 📄 VIEW SYSTEM PROTOCOL 📘", reply_markup=None)
        protocol_sequence = [
            TimedMessage(text="📄 <b>System Protocol Overview (Simplified Extract)</b>:\n<i>All access nodes are subject to periodic stability and alignment checks...</i>", delay_before=1.0),
            TimedMessage(text="🛡 System audit indicates non-standard signal detected on your node.", delay_before=2.8),
            TimedMessage(text="⚠️ <b>SYSTEM FLAG ACTIVE.</b>\nYou are advised to proceed to Step ②.", delay_before=2.2),
        ]
        await send_delayed_sequence(context.bot, query.message.chat_id, protocol_sequence, initial_delay=0.5)
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.5) 
        keyboard_step2 = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ PROCEED TO STEP ②", callback_data=CALLBACK_S2_FROM_PROTOCOL)]])
        await context.bot.send_message(chat_id=query.message.chat_id, text="Proceed when ready:", reply_markup=keyboard_step2, parse_mode=ParseMode.HTML)
        context.user_data["entry_point_s2"] = "from_protocol"
        context.user_data["current_flow_step"] = AWAITING_STEP_2_FROM_PROTOCOL
        logger.info(f"User {user_id} viewed protocol. Status: {AWAITING_STEP_2_FROM_PROTOCOL}")
    except Exception as e:
        await send_system_error_reply(query, context, user_id, "An error occurred displaying protocol.")


async def s1_ignore_warning_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        if query: await query.answer()
        return
    user_id = user.id
    logger.info(f"BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_IGNORE_WARNING} at {datetime.datetime.utcnow().isoformat()}Z")
    await query.answer("Processing decision...")
    try:
        await query.edit_message_text(text="ACTION SELECTED: ⛔️ IGNORE SYSTEM WARNING", reply_markup=None)
        user_secure_id = context.user_data.get("secure_id", "UNKNOWN_NODE")
        ignore_sequence = [
            TimedMessage(text=f"🔴 <b>WARNING IGNORED</b>\n<i>Node <code>{user_secure_id}</code> flagged for instability.</i>", delay_before=0.7, typing=False),
            TimedMessage(text="🤖 <b>SYSTEM INTERVENTION ENGAGED</b>\nOverride protocol initializing...", delay_before=1.5),
            TimedMessage(text="🔐 Enforcement directive issued. You are now subject to forced TRACE_DIAGNOSTIC.", delay_before=2.5),
            TimedMessage(text="🚨 <b>Redirecting to Step ②: TRACE_REPORT_Δ7</b>", delay_before=2.0),
        ]
        await send_delayed_sequence(context.bot, query.message.chat_id, ignore_sequence, initial_delay=0.5)
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.6) 
        keyboard_step2 = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ CONTINUE UNDER SYSTEM OVERRIDE", callback_data=CALLBACK_S2_FROM_IGNORE)]])
        await context.bot.send_message(chat_id=query.message.chat_id, text="System will proceed on your behalf:", reply_markup=keyboard_step2, parse_mode=ParseMode.HTML)
        context.user_data["entry_point_s2"] = "from_ignore"
        context.user_data["ignored_critical_warning_step1"] = True
        context.user_data["current_flow_step"] = AWAITING_STEP_2_FROM_IGNORE
        logger.warning(f"User {user_id} ignored warning. Status: {AWAITING_STEP_2_FROM_IGNORE}")
    except Exception as e:
        await send_system_error_reply(query, context, user_id, "An error occurred processing your decision.")


async def step_2_entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (This function's internal pacing was already reviewed and seems reasonable, keeping as is for now)
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        if query: await query.answer()
        return
    user_id = user.id
    logger.info(f"BUTTON_CLICK: User {user_id} clicked Step 2 entry button (cb_data: {query.data}) at {datetime.datetime.utcnow().isoformat()}Z")
    await query.answer()
    try:
        await query.edit_message_text(
            text="✅ <b>STEP ① COMPLETE — Action Confirmed.</b>\n\n➡️ Proceeding to Step ②...",
            reply_markup=None, parse_mode=ParseMode.HTML
        )
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.0) 
        source_entry = context.user_data.get("entry_point_s2", "unknown_s2_entry")
        logger.info(f"User {user_id} entering Step 2 from: {source_entry}")
        opening_message_s2 = ""
        if source_entry == "from_ignore":
            opening_message_s2 = ("⚠️ <b>SYSTEM OVERRIDE PROTOCOL ACTIVE.</b>\nYour decision to bypass safety checks has been logged.\nForced alignment analysis underway via TRACE_REPORT_Δ7.")
            context.user_data["risk_score"] = 1.0
        elif source_entry == "from_protocol":
            opening_message_s2 = ("📘 <b>PROTOCOL ACKNOWLEDGED.</b>\nYour review of system procedures. Proceeding with standard TRACE_REPORT_Δ7 analysis.")
            context.user_data["risk_score"] = 0.5
        else: # from_diagnostic or unknown
            opening_message_s2 = ("🧠 <b>DIAGNOSTIC RESPONSE LOGGED.</b>\nLaunching TRACE_REPORT_Δ7 to trace alignment anomalies found in Phase 1.")
            context.user_data["risk_score"] = 0.2
        step2_messages_after_opening = [
            TimedMessage(text=opening_message_s2, delay_before=1.5),
            TimedMessage(
                text="🧩 <b>STEP ②: TRACE_REPORT_Δ7 ANALYSIS</b> 🧩\n\nScanning ΔPrime vectors...\nCorrelating signal drift patterns...\nPlease allow a moment for the system to compile the report.",
                delay_before=1.8
            )
        ]
        await send_delayed_sequence(context.bot, query.message.chat_id, step2_messages_after_opening, initial_delay=0.2)
        context.user_data["current_flow_step"] = STEP_2_STARTED_ANALYSIS
        logger.info(f"User {user_id} has started Step 2 analysis. Status: {STEP_2_STARTED_ANALYSIS}, Risk Score: {context.user_data.get('risk_score')}")
    except Exception as e:
        await send_system_error_reply(query, context, user_id, "A system error occurred while proceeding to Step ②.")