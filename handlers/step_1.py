import asyncio
import logging
import datetime # Retained for internal logging timestamps
import hashlib # For the placeholder generate_user_secure_id
from dataclasses import dataclass # For ❗设计建议 4
from typing import List, Optional # For type hinting

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError # For more specific error handling

# --- 临时的 generate_user_secure_id 占位符 ---
def generate_user_secure_id(user_id_str: str) -> str:
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
# ... (其他状态常量保持不变)
STEP_2_STARTED_ANALYSIS = "step_2_started_analysis"


# --- ❗设计建议 4：send_delayed_sequence 可改为更强结构 (dataclass) ---
@dataclass
class TimedMessage:
    text: str
    delay_before: float = 0.8  # Default delay before sending this message
    typing: bool = True
    # reply_to_message_id: Optional[int] = None # ❗逻辑风险 1 (暂时不直接用，因为我们编辑原按钮消息)


# --- 辅助函数: send_delayed_sequence (应用优化) ---
async def send_delayed_sequence(
    bot, 
    chat_id: int, 
    sequence: List[TimedMessage], 
    initial_delay: float = 0
) -> None:
    if initial_delay > 0:
        await asyncio.sleep(initial_delay)

    for item in sequence:
        if item.typing and item.delay_before > 0.2: # Only show typing if delay is noticeable
            try:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except TelegramError as e_chat_action: # More specific error
                logger.warning(f"Failed to send chat action in chat {chat_id}: {e_chat_action}")
        
        if item.delay_before > 0:
            await asyncio.sleep(item.delay_before)
        
        # ❗逻辑风险 3：send_delayed_sequence() 无容错处理 (添加try-except)
        try:
            # reply_to_id = item.reply_to_message_id if item.reply_to_message_id else None # Not used yet
            await bot.send_message(
                chat_id=chat_id, 
                text=item.text, 
                parse_mode=ParseMode.HTML
                # reply_to_message_id=reply_to_id # Future: if needed
            )
        except TelegramError as e_send: # Catch specific Telegram errors
            logger.warning(f"Failed to send message in sequence to chat {chat_id}: '{item.text[:30]}...' due to {e_send}")
        except Exception as e_general: # Catch other unexpected errors
            logger.error(f"Unexpected error sending message in sequence to chat {chat_id}: '{item.text[:30]}...' due to {e_general}", exc_info=True)


# --- 统一 fallback 错误回复语句 (保持不变) ---
async def send_system_error_reply(target_object, context, user_id="Unknown", error_text="..."): # ... (内容同前)
    logger.error(f"Sending system error reply to user {user_id}: {error_text}")
    try:
        reply_target = None
        if target_object and hasattr(target_object, 'message') and target_object.message:
            reply_target = target_object.message
        elif target_object and hasattr(target_object, 'reply_html'): 
            reply_target = target_object
        if reply_target and hasattr(reply_target, 'reply_html'):
             await reply_target.reply_html(f"⚠️ <b>SYSTEM ERROR:</b>\n{error_text}")
        elif user_id != "Unknown" and context.bot:
            await context.bot.send_message(chat_id=user_id, text=f"⚠️ <b>SYSTEM ERROR:</b>\n{error_text}", parse_mode=ParseMode.HTML)
    except Exception as e_reply:
        logger.error(f"CRITICAL: Failed to send system error reply to user {user_id}: {e_reply}")


async def start_step_1_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: # ... (保持不变)
        return
    user = update.effective_user # ... (保持不变)
    if not user: # ... (保持不变)
        await send_system_error_reply(update.message, context, "UnknownUserOnInit", "User identification failed.")
        return
    user_id = user.id # ... (保持不变)
    current_step = context.user_data.get("current_flow_step", "") # ... (保持不变)
    entry_point_s2_stale = context.user_data.get("entry_point_s2", "") # ... (保持不变)
    if update.message.text == "/start" and current_step.startswith("AWAITING_STEP_2_FROM_"): # ... (保持不变)
        await update.message.reply_html("⚠️ <b>System State Inconsistency Detected.</b>...")
        context.user_data.pop("current_flow_step", None); # ... (保持不变)
        logger.info(f"User {user_id} stale AWAITING_STEP_2 state cleared by /start...")
    # ... (secure_id generation - 保持不变) ...
    logger.info(f"User {user_id} ({user.username or 'N/A'}) started step_1_flow. Current step before: {current_step}")
    secure_id = generate_user_secure_id(str(user_id))
    context.user_data["secure_id"] = secure_id

    try:
        # ❗逻辑风险 2：首次进入 start_step_1_flow 时 message.reply_html() 全程使用 (优化)
        # 前1-2条作为 reply_html (嵌入对话)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(0.5)
        await update.message.reply_html("🔷 ACCESS NODE CONFIRMED\n→ PROTOCOL [Z1-GRAY_ΔPRIME] INITIALIZED")
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(1.5) # Delay after first reply
        message_text_2 = (
            f"🔹 SECURE IDENTIFIER GENERATED\n"
            f"→ USER_SECURE_ID: <code>{secure_id}</code>\n"
            f"→ AUTH_LAYER: 2B | SYNC_STATUS: PENDING"
        )
        await update.message.reply_html(message_text_2) # Second message also as reply

        # 后续使用 send_message() (通过 send_delayed_sequence) 单独发出，配合 typing 分离行为
        start_flow_part2_sequence = [
            TimedMessage(text="⚠️ INITIAL NODE ANALYSIS: CRITICAL WARNING\n→ STABILITY RISK INDEX: 0.84 (ABOVE THRESHOLD)\n→ TRACE_SIGNAL: NON-STANDARD ALIGNMENT", delay_before=2.7),
            TimedMessage(text="🔒 SYSTEM ALERT: Your access node has entered a volatility state.\n→ Interruption may trigger node quarantine protocol.", delay_before=4.5),
            TimedMessage(text="🧠 ACTION REQUIRED: Begin full TRACE_DIAGNOSTIC to determine node viability.\n→ Delayed response = elevated risk of deactivation", delay_before=3.2)
        ]
        await send_delayed_sequence(context.bot, update.effective_chat.id, start_flow_part2_sequence, initial_delay=0.6) # Small initial delay after last reply

        # 发送按钮选择（作为新消息）
        keyboard = [
            [InlineKeyboardButton("🧪 RUN TRACE_DIAGNOSTIC NOW ⚡️", callback_data=CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN)],
            [InlineKeyboardButton("📄 VIEW SYSTEM PROTOCOL 📘", callback_data=CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW)],
            [InlineKeyboardButton("⛔️ IGNORE SYSTEM WARNING (NOT RECOMMENDED)", callback_data=CALLBACK_S1_IGNORE_WARNING)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(2.8) # Delay before showing buttons
        await context.bot.send_message(chat_id=update.effective_chat.id, text="SELECT ACTION:", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        
        context.user_data["current_flow_step"] = AWAITING_STEP_1_BUTTON
        logger.info(f"User {user_id}: current_flow_step set to {AWAITING_STEP_1_BUTTON}.")
    except Exception as e: # ... (保持不变)
        await send_system_error_reply(update.message, context, user_id, "System communication error during initialization.")

# --- Callback Handlers (应用 send_delayed_sequence 和 TimedMessage) ---

async def s1_initiate_diagnostic_scan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query # ... (保持不变)
    user = update.effective_user # ... (保持不变)
    if not query or not query.message or not user: # ... (保持不变)
        if query: await query.answer()
        return
    user_id = user.id # ... (保持不变)
    logger.info(f"BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN} at {datetime.datetime.utcnow().isoformat()}Z")
    await query.answer("Processing...")
    try:
        await query.edit_message_text(text="ACTION SELECTED: 🧪 RUN TRACE_DIAGNOSTIC NOW ⚡️", reply_markup=None)
        
        diagnostic_sequence = [
            TimedMessage(text="🔬 <b>TRACE_DIAGNOSTIC INITIATED...</b>\nAnalyzing node stability signatures...", delay_before=1.2),
            TimedMessage(text="🧠 Analyzing ΔPrime vector clusters...", delay_before=2.8),
            TimedMessage(text="📡 Signal drift detected... calibrating...", delay_before=2.4),
            TimedMessage(text="✅ <b>DIAGNOSTIC PHASE 1 COMPLETE.</b>", delay_before=1.2, typing=False),
            TimedMessage(text="<b>ALIGNMENT ANOMALIES DETECTED</b>\n\nYour node trace reveals core-misalignment clusters requiring deeper analysis.", delay_before=2.0),
            TimedMessage(text="🧠 <b>Proceed to Step ②: TRACE_REPORT_Δ7</b> for critical breakdown.", delay_before=1.4),
        ]
        await send_delayed_sequence(context.bot, query.message.chat_id, diagnostic_sequence, initial_delay=0.8)

        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(0.6)
        keyboard_step2 = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ CONTINUE TO STEP ②", callback_data=CALLBACK_S2_FROM_DIAGNOSTIC)]])
        await context.bot.send_message(chat_id=query.message.chat_id, text="Ready to continue?", reply_markup=keyboard_step2, parse_mode=ParseMode.HTML)
        
        context.user_data["entry_point_s2"] = "from_diagnostic" # ... (保持不变)
        context.user_data["current_flow_step"] = AWAITING_STEP_2_FROM_DIAGNOSTIC # ... (保持不变)
        logger.info(f"User {user_id} completed diagnostic. Status: {AWAITING_STEP_2_FROM_DIAGNOSTIC}")
    except Exception as e: # ... (保持不变)
        await send_system_error_reply(query, context, user_id, "An error occurred during diagnostic.")

async def s1_view_protocol_overview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query # ... (保持不变)
    user = update.effective_user # ... (保持不变)
    if not query or not query.message or not user: # ... (保持不变)
        if query: await query.answer()
        return
    user_id = user.id # ... (保持不变)
    logger.info(f"BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW} at {datetime.datetime.utcnow().isoformat()}Z")
    await query.answer()
    try:
        await query.edit_message_text(text="ACTION SELECTED: 📄 VIEW SYSTEM PROTOCOL 📘", reply_markup=None)
        
        protocol_sequence = [
            TimedMessage(text="📄 <b>System Protocol Overview (Simplified Extract)</b>:\n<i>All access nodes are subject to periodic stability and alignment checks. Non-standard signal patterns or deviations from baseline parameters (ΔPrime) may indicate potential desynchronization risks. Active diagnostic measures are recommended to ensure continued node viability and prevent automated quarantine protocols.</i>", delay_before=0.8),
            TimedMessage(text="🛡 System audit indicates non-standard signal detected on your node.", delay_before=2.5),
            TimedMessage(text="⚠️ <b>SYSTEM FLAG ACTIVE.</b>\nYou are advised to proceed to Step ②.", delay_before=2.0),
        ]
        await send_delayed_sequence(context.bot, query.message.chat_id, protocol_sequence)

        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.2)
        keyboard_step2 = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ PROCEED TO STEP ②", callback_data=CALLBACK_S2_FROM_PROTOCOL)]])
        await context.bot.send_message(chat_id=query.message.chat_id, text="Proceed when ready:", reply_markup=keyboard_step2, parse_mode=ParseMode.HTML)
        
        context.user_data["entry_point_s2"] = "from_protocol" # ... (保持不变)
        context.user_data["current_flow_step"] = AWAITING_STEP_2_FROM_PROTOCOL # ... (保持不变)
        logger.info(f"User {user_id} viewed protocol. Status: {AWAITING_STEP_2_FROM_PROTOCOL}")
    except Exception as e: # ... (保持不变)
        await send_system_error_reply(query, context, user_id, "An error occurred displaying protocol.")

async def s1_ignore_warning_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query # ... (保持不变)
    user = update.effective_user # ... (保持不变)
    if not query or not query.message or not user: # ... (保持不变)
        if query: await query.answer()
        return
    user_id = user.id # ... (保持不变)
    logger.info(f"BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_IGNORE_WARNING} at {datetime.datetime.utcnow().isoformat()}Z")
    await query.answer("Processing decision...")
    try:
        await query.edit_message_text(text="ACTION SELECTED: ⛔️ IGNORE SYSTEM WARNING", reply_markup=None)
        user_secure_id = context.user_data.get("secure_id", "UNKNOWN_NODE")
        
        ignore_sequence = [
            TimedMessage(text=f"🔴 <b>WARNING IGNORED</b>\n<i>Node <code>{user_secure_id}</code> flagged for instability.</i>", delay_before=0.5, typing=False),
            TimedMessage(text="🤖 <b>SYSTEM INTERVENTION ENGAGED</b>\nOverride protocol initializing...", delay_before=1.0),
            TimedMessage(text="🔐 Enforcement directive issued. You are now subject to forced TRACE_DIAGNOSTIC.", delay_before=2.2),
            TimedMessage(text="🚨 <b>Redirecting to Step ②: TRACE_REPORT_Δ7</b>", delay_before=1.8),
        ]
        await send_delayed_sequence(context.bot, query.message.chat_id, ignore_sequence)

        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.4)
        keyboard_step2 = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ CONTINUE UNDER SYSTEM OVERRIDE", callback_data=CALLBACK_S2_FROM_IGNORE)]])
        await context.bot.send_message(chat_id=query.message.chat_id, text="System will proceed on your behalf:", reply_markup=keyboard_step2, parse_mode=ParseMode.HTML)
        
        context.user_data["entry_point_s2"] = "from_ignore" # ... (保持不变)
        context.user_data["ignored_critical_warning_step1"] = True # ... (保持不变)
        context.user_data["current_flow_step"] = AWAITING_STEP_2_FROM_IGNORE # ... (保持不变)
        logger.warning(f"User {user_id} ignored warning. Status: {AWAITING_STEP_2_FROM_IGNORE}")
    except Exception as e: # ... (保持不变)
        await send_system_error_reply(query, context, user_id, "An error occurred processing your decision.")

async def step_2_entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query # ... (保持不变)
    user = update.effective_user # ... (保持不变)
    if not query or not query.message or not user: # ... (保持不变)
        if query: await query.answer()
        return
    user_id = user.id # ... (保持不变)
    logger.info(f"BUTTON_CLICK: User {user_id} clicked Step 2 entry button (cb_data: {query.data}) at {datetime.datetime.utcnow().isoformat()}Z")
    await query.answer()
    try:
        await query.edit_message_text(
            text="✅ <b>STEP ① COMPLETE — Action Confirmed.</b>\n\n➡️ Proceeding to Step ②...",
            reply_markup=None, parse_mode=ParseMode.HTML
        )
        
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.0) 

        source_entry = context.user_data.get("entry_point_s2", "unknown_s2_entry") # ... (保持不变)
        logger.info(f"User {user_id} entering Step 2 from: {source_entry}") # ... (保持不变)

        opening_message_s2 = "" # ... (个性化开场白逻辑保持不变，内容也保持不变)
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
            TimedMessage(text=opening_message_s2, delay_before=1.5), # Was 1.2, adjusted
            TimedMessage(
                text="🧩 <b>STEP ②: TRACE_REPORT_Δ7 ANALYSIS</b> 🧩\n\nScanning ΔPrime vectors...\nCorrelating signal drift patterns...\nPlease allow a moment for the system to compile the report.",
                delay_before=1.8 # Was 1.2, adjusted
            )
        ]
        await send_delayed_sequence(context.bot, query.message.chat_id, step2_messages_after_opening, initial_delay=0.2) # Small initial delay
        
        context.user_data["current_flow_step"] = STEP_2_STARTED_ANALYSIS # ... (保持不变)
        logger.info(f"User {user_id} has started Step 2 analysis. Status: {STEP_2_STARTED_ANALYSIS}, Risk Score: {context.user_data.get('risk_score')}")
    except Exception as e: # ... (保持不变)
        await send_system_error_reply(query, context, user_id, "A system error occurred while proceeding to Step ②.")