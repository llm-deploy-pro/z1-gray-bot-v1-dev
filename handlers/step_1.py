import asyncio
import logging
import datetime
import hashlib # For the placeholder generate_user_secure_id

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

# --- 临时的 generate_user_secure_id 占位符 ---
def generate_user_secure_id(user_id_str: str) -> str:
    """Generates a placeholder secure ID."""
    return hashlib.md5(user_id_str.encode()).hexdigest()[:16]
# --- End of placeholder ---

logger = logging.getLogger(__name__)

# --- Callback Data Constants for Step 1 ---
CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN = "s1_initiate_diagnostic_scan"
CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW = "s1_view_protocol_overview"
CALLBACK_S1_IGNORE_WARNING = "s1_ignore_warning"

# --- Callback Data Constants for Step 2 Entry Points ---
CALLBACK_S2_FROM_DIAGNOSTIC = "step2_entry_from_diagnostic"
CALLBACK_S2_FROM_PROTOCOL = "step2_entry_from_protocol"
CALLBACK_S2_FROM_IGNORE = "step2_entry_from_ignore"

# --- Flow State Constants for user_data["current_flow_step"] ---
AWAITING_STEP_1_BUTTON = "AWAITING_STEP_1_BUTTON"
AWAITING_STEP_2_FROM_DIAGNOSTIC = "AWAITING_STEP_2_FROM_DIAGNOSTIC"
AWAITING_STEP_2_FROM_PROTOCOL = "AWAITING_STEP_2_FROM_PROTOCOL"
AWAITING_STEP_2_FROM_IGNORE = "AWAITING_STEP_2_FROM_IGNORE"
STEP_1_DIAGNOSTIC_RUNNING = "STEP_1_DIAGNOSTIC_RUNNING"
STEP_2_STARTED_ANALYSIS = "step_2_started_analysis"

# --- ❗问题 3：统一 fallback 错误回复语句 ---
async def send_system_error_reply(
    target_object: Update | None, # Can be Update or query.message
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int | str = "Unknown",
    error_text: str = "An unexpected system error occurred. Please try the /start sequence again."
) -> None:
    """Sends a standardized system error reply."""
    logger.error(f"Sending system error reply to user {user_id}: {error_text}")
    try:
        if target_object and hasattr(target_object, 'message') and target_object.message: # For CallbackQuery
             await target_object.message.reply_html(f"⚠️ <b>SYSTEM ERROR:</b>\n{error_text}")
        elif target_object and hasattr(target_object, 'reply_html'): # For Message object in Update
             await target_object.reply_html(f"⚠️ <b>SYSTEM ERROR:</b>\n{error_text}")
        elif user_id != "Unknown" and context.bot: # Fallback to sending a new message if target_object is problematic
            await context.bot.send_message(chat_id=user_id, text=f"⚠️ SYSTEM ERROR:\n{error_text}", parse_mode=ParseMode.HTML)
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

    # ❗问题1：/start 回退逻辑提示正确，但未真正“恢复流程” (改进提示，为未来恢复做铺垫)
    if update.message.text == "/start" and current_step.startswith("AWAITING_STEP_2_FROM_"):
        logger.warning(
            f"User {user_id} (State: {current_step}, Entry: {entry_point_s2_stale}) initiated /start while awaiting Step 2. "
            "Current recovery: Inform and restart Step 1."
        )
        await update.message.reply_html(
            "⚠️ <b>System State Inconsistency Detected.</b>\n"
            "Your previous session was awaiting entry into Step ②. "
            "For now, we will restart the initialization sequence. "
            "If this issue persists, please contact support."
            # Future: "Alternatively, you can try to /resume_step2 if available."
        )
        # Clear stale state to ensure a clean Step 1 restart
        context.user_data.pop("current_flow_step", None)
        context.user_data.pop("entry_point_s2", None)
        context.user_data.pop("risk_score", None) # Also clear risk_score if set
        # Fall through to normal Step 1 start after this message
        logger.info(f"User {user_id} stale AWAITING_STEP_2 state cleared by /start. Proceeding with fresh Step 1.")

    logger.info(f"User {user_id} ({user.username or 'N/A'}) started step_1_flow. Current step before: {current_step}")
    secure_id = generate_user_secure_id(str(user_id))
    context.user_data["secure_id"] = secure_id

    try:
        # ... (Step 1 messages - no changes from previous version) ...
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html("🔷 ACCESS NODE CONFIRMED\n→ PROTOCOL [Z1-GRAY_ΔPRIME] INITIALIZED")
        await asyncio.sleep(1.5)
        timestamp_str = datetime.datetime.utcnow().strftime('%H:%M:%S.%f')[:-3] + ' UTC'
        message_text_2 = (
            f"→ TIMESTAMP: {timestamp_str}\n"
            f"🔹 SECURE IDENTIFIER GENERATED\n"
            f"→ USER_SECURE_ID: <code>{secure_id}</code>\n"
            f"→ AUTH_LAYER: 2B | SYNC_STATUS: PENDING"
        )
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html(message_text_2)
        await asyncio.sleep(2.7)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html(
            "⚠️ INITIAL NODE ANALYSIS: CRITICAL WARNING\n"
            "→ STABILITY RISK INDEX: 0.84 (ABOVE THRESHOLD)\n"
            "→ TRACE_SIGNAL: NON-STANDARD ALIGNMENT"
        )
        await asyncio.sleep(4.5)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html(
            "🔒 SYSTEM ALERT: Your access node has entered a volatility state.\n"
            "→ Interruption may trigger node quarantine protocol."
        )
        await asyncio.sleep(3.2)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html(
            "🧠 ACTION REQUIRED: Begin full TRACE_DIAGNOSTIC to determine node viability.\n"
            "→ Delayed response = elevated risk of deactivation"
        )
        await asyncio.sleep(2.8)
        # ... (End of Step 1 messages) ...
        keyboard = [
            [InlineKeyboardButton("🧪 RUN TRACE_DIAGNOSTIC NOW ⚡️", callback_data=CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN)],
            [InlineKeyboardButton("📄 VIEW SYSTEM PROTOCOL 📘", callback_data=CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW)],
            [InlineKeyboardButton("⛔️ IGNORE SYSTEM WARNING (NOT RECOMMENDED)", callback_data=CALLBACK_S1_IGNORE_WARNING)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html("SELECT ACTION:", reply_markup=reply_markup)
        context.user_data["current_flow_step"] = AWAITING_STEP_1_BUTTON
        logger.info(f"User {user_id}: current_flow_step set to {AWAITING_STEP_1_BUTTON}.")
    except Exception as e:
        logger.error(f"Error in start_step_1_flow for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(update.message, context, user_id, "System communication error during initialization.")


async def s1_initiate_diagnostic_scan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        logger.warning("s1_initiate_diagnostic_scan_callback: Missing query, message, or user.")
        if query: await query.answer()
        return
    
    user_id = user.id
    # ❗问题 4：日志记录没有跟踪 “按钮点击行为路径 + 时间”
    logger.info(f"BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN} at {datetime.datetime.utcnow().isoformat()}Z")
    
    await query.answer("Processing...")
    try:
        await query.edit_message_text(text="ACTION SELECTED: 🧪 RUN TRACE_DIAGNOSTIC NOW ⚡️", reply_markup=None)
        await query.message.reply_html("🔬 ANALYZING NODE STABILITY SIGNATURES...\nPLEASE STAND BY.")
        await asyncio.sleep(4.2)
        await query.message.reply_html("✅ <b>DIAGNOSTIC PHASE 1 COMPLETE.</b>")
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING) # For Step 2 intro
        await asyncio.sleep(0.8)
        await query.message.reply_html(
            "<b>ALIGNMENT ANOMALIES DETECTED</b>\n\n"
            "Your node trace reveals core-misalignment clusters requiring deeper analysis.\n"
            "🧠 <b>Proceed to Step ②: TRACE_REPORT_Δ7</b> for critical breakdown."
        )
        keyboard_step2 = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ CONTINUE TO STEP ②", callback_data=CALLBACK_S2_FROM_DIAGNOSTIC)]])
        await query.message.reply_html("Ready to continue?", reply_markup=keyboard_step2)
        context.user_data["entry_point_s2"] = "from_diagnostic"
        context.user_data["current_flow_step"] = AWAITING_STEP_2_FROM_DIAGNOSTIC
        logger.info(f"User {user_id} completed diagnostic, proceeding to Step 2. Entry: from_diagnostic. Status: {AWAITING_STEP_2_FROM_DIAGNOSTIC}")
    except Exception as e:
        logger.error(f"Error in s1_initiate_diagnostic_scan_callback for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(query, context, user_id, "An error occurred during diagnostic.")


async def s1_view_protocol_overview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        logger.warning("s1_view_protocol_overview_callback: Missing query, message, or user.")
        if query: await query.answer()
        return
        
    user_id = user.id
    logger.info(f"BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW} at {datetime.datetime.utcnow().isoformat()}Z")

    await query.answer()
    try:
        await query.edit_message_text(text="ACTION SELECTED: 📄 VIEW SYSTEM PROTOCOL 📘", reply_markup=None)
        protocol_text = (
            "📄 <b>System Protocol Overview</b> (Simplified Extract):\n\n"
            "<i>All access nodes are subject to periodic stability and alignment checks. " # ... (rest of protocol text)
        )
        await query.message.reply_html(protocol_text)
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(0.8)
        await query.message.reply_html(
            "⚠️ <b>SYSTEM FLAG ACTIVE.</b>\n"
            "You are advised to proceed directly to Step ②: ALIGNMENT TRACE REPORT."
        )
        keyboard_step2 = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ PROCEED TO STEP ②", callback_data=CALLBACK_S2_FROM_PROTOCOL)]])
        await query.message.reply_html("Proceed when ready:", reply_markup=keyboard_step2)
        context.user_data["entry_point_s2"] = "from_protocol"
        context.user_data["current_flow_step"] = AWAITING_STEP_2_FROM_PROTOCOL
        logger.info(f"User {user_id} viewed protocol, proceeding to Step 2. Entry: from_protocol. Status: {AWAITING_STEP_2_FROM_PROTOCOL}")
    except Exception as e:
        logger.error(f"Error in s1_view_protocol_overview_callback for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(query, context, user_id, "An error occurred displaying protocol.")


async def s1_ignore_warning_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        logger.warning("s1_ignore_warning_callback: Missing query, message, or user.")
        if query: await query.answer()
        return
    
    user_id = user.id
    logger.info(f"BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_IGNORE_WARNING} at {datetime.datetime.utcnow().isoformat()}Z")

    await query.answer("Processing decision...")
    try:
        await query.edit_message_text(text="ACTION SELECTED: ⛔️ IGNORE SYSTEM WARNING", reply_markup=None)
        user_secure_id = context.user_data.get("secure_id", "UNKNOWN_NODE")
        warning_text = (
            f"🔴 <b>WARNING IGNORED — SYSTEM OVERRIDE ENGAGED</b>\n\n"
            f"<i>Node <code>{user_secure_id}</code> instability detected.\n" # ... (rest of warning text)
        )
        await query.message.reply_html(warning_text)
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(0.8)
        keyboard_step2 = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ CONTINUE UNDER SYSTEM OVERRIDE", callback_data=CALLBACK_S2_FROM_IGNORE)]])
        await query.message.reply_html("System will proceed on your behalf.", reply_markup=keyboard_step2)
        context.user_data["entry_point_s2"] = "from_ignore"
        context.user_data["ignored_critical_warning_step1"] = True
        context.user_data["current_flow_step"] = AWAITING_STEP_2_FROM_IGNORE
        logger.warning(f"User {user_id} ignored warning, proceeding to Step 2 under override. Entry: from_ignore. Status: {AWAITING_STEP_2_FROM_IGNORE}")
    except Exception as e:
        logger.error(f"Error in s1_ignore_warning_callback for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(query, context, user_id, "An error occurred processing your decision.")


async def step_2_entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user: # query.message is the message with the "CONTINUE TO STEP 2" button
        logger.warning("step_2_entry_handler: Missing query, message, or user.")
        if query: await query.answer()
        return

    user_id = user.id
    logger.info(f"BUTTON_CLICK: User {user_id} clicked Step 2 entry button (cb_data: {query.data}) at {datetime.datetime.utcnow().isoformat()}Z")
    
    await query.answer()
    try:
        await query.edit_message_text(
            text="✅ <b>STEP ① COMPLETE — Action Confirmed.</b>\n\n➡️ Proceeding to Step ②...",
            reply_markup=None,
            parse_mode=ParseMode.HTML
        )

        source_entry = context.user_data.get("entry_point_s2", "unknown_s2_entry")
        logger.info(f"User {user_id} entering Step 2 from: {source_entry}")

        opening_message_s2 = ""
        if source_entry == "from_ignore":
            opening_message_s2 = "..." # As defined before
            context.user_data["risk_score"] = 1.0
        elif source_entry == "from_protocol":
            opening_message_s2 = "..." # As defined before
            context.user_data["risk_score"] = 0.5
        else: # from_diagnostic or unknown
            opening_message_s2 = "..." # As defined before
            context.user_data["risk_score"] = 0.2
        
        # ❗问题 2：Step 2 内部 await query.message.reply_html(...) 多次调用未做 UI 层逻辑判定 (优化)
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.2) # Artificial delay for better UX pacing
        await query.message.reply_html(opening_message_s2) # Send the tailored opening

        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.8) # Another delay

        await query.message.reply_html(
            "🧩 <b>STEP ②: TRACE_REPORT_Δ7 ANALYSIS</b> 🧩\n\n"
            "Scanning ΔPrime vectors...\n"
            "Correlating signal drift patterns...\n"
            "Please allow a moment for the system to compile the report."
        )
        context.user_data["current_flow_step"] = STEP_2_STARTED_ANALYSIS
        logger.info(f"User {user_id} has started Step 2 analysis. Status: {STEP_2_STARTED_ANALYSIS}, Risk Score: {context.user_data.get('risk_score')}")
        # ... (Further Step 2 logic would go here) ...
    except Exception as e:
        logger.error(f"Error in step_2_entry_handler for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(query, context, user_id, "A system error occurred while proceeding to Step ②.")