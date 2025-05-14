import asyncio
import logging
import datetime
from typing import List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from utils.helpers import TimedMessage, send_delayed_sequence, generate_user_secure_id, send_system_error_reply
from handlers.step_2 import execute_step_2_scan_sequence

logger = logging.getLogger(__name__)

CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN = "s1_initiate_diagnostic_scan"
CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW = "s1_view_protocol_overview"
CALLBACK_S1_IGNORE_WARNING = "s1_ignore_warning"
CALLBACK_S2_FROM_DIAGNOSTIC = "step2_entry_from_diagnostic"
CALLBACK_S2_FROM_PROTOCOL = "step2_entry_from_protocol"
CALLBACK_S2_FROM_IGNORE = "step2_entry_from_ignore"

AWAITING_STEP_1_BUTTON = "AWAITING_STEP_1_BUTTON"
AWAITING_STEP_2_FROM_DIAGNOSTIC = "AWAITING_STEP_2_FROM_DIAGNOSTIC"
AWAITING_STEP_2_FROM_PROTOCOL = "AWAITING_STEP_2_FROM_PROTOCOL"
AWAITING_STEP_2_FROM_IGNORE = "AWAITING_STEP_2_FROM_IGNORE"
STEP_2_STARTED_ANALYSIS = "step_2_started_analysis"


async def start_step_1_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        logger.warning("start_step_1_flow called without a message or effective_chat.")
        return

    user = update.effective_user
    if not user:
        logger.warning("Effective user is None in start_step_1_flow.")
        await send_system_error_reply(update, context, "UnknownUserOnInit", "User identification failed.")
        return

    user_id = user.id
    context.user_data["user_id"] = user_id
    current_step = context.user_data.get("current_flow_step", "")

    active_flow_states = [
        AWAITING_STEP_1_BUTTON, AWAITING_STEP_2_FROM_DIAGNOSTIC,
        AWAITING_STEP_2_FROM_PROTOCOL, AWAITING_STEP_2_FROM_IGNORE,
        STEP_2_STARTED_ANALYSIS, "step_2_scan_complete_awaiting_s3"
    ]
    if update.message.text == "/start" and current_step in active_flow_states:
        logger.warning(
            f"[Step ①] User {user_id} (State: {current_step}) initiated /start mid-flow. "
            "Clearing relevant state and restarting Step 1."
        )
        await update.message.reply_html(
            "⚠️ <b>System State Inconsistency Detected.</b>\n"
            "Your previous session was interrupted. "
            "For system integrity, we will restart the initialization sequence."
        )
        keys_to_pop = ["current_flow_step", "entry_point_s2", "risk_score", "secure_id", "ignored_critical_warning_step1"]
        for key in keys_to_pop:
            context.user_data.pop(key, None)
        logger.info(f"[Step ①] User {user_id} stale flow state cleared by /start. Proceeding with fresh Step 1.")

    logger.info(f"[Step ①] User {user_id} ({user.username or 'N/A'}) started step_1_flow. Current step before this execution: {current_step}")
    secure_id = generate_user_secure_id(user_id)
    context.user_data["secure_id"] = secure_id

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(0.5)
        await update.message.reply_html("🔷 ACCESS NODE CONFIRMED\n→ PROTOCOL [Z1-GRAY_ΔPRIME] INITIALIZED")

        await asyncio.sleep(1.5)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(0.6)
        message_text_2 = (
            f"🔹 SECURE IDENTIFIER GENERATED\n"
            f"→ USER_SECURE_ID: <code>{secure_id}</code>\n"
            f"→ AUTH_LAYER: 2B | SYNC_STATUS: PENDING"
        )
        await update.message.reply_html(message_text_2)

        await asyncio.sleep(2.7)
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
        logger.info(f"[Step ①] User {user_id}: current_flow_step set to {AWAITING_STEP_1_BUTTON}.")

    except Exception as e:
        logger.error(f"Error in start_step_1_flow for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(update, context, user_id, "System communication error during initialization.")


async def s1_initiate_diagnostic_scan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        if query: await query.answer()
        return

    user_id = user.id
    context.user_data["user_id"] = user_id
    logger.info(f"[Step ①] BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN}")
    await query.answer("Processing...")
    try:
        await query.edit_message_text(text="ACTION SELECTED: 🧪 RUN TRACE_DIAGNOSTIC NOW ⚡️", reply_markup=None)
        diagnostic_sequence = [
            TimedMessage(text="🔬 <b>TRACE_DIAGNOSTIC INITIATED...</b>\nAnalyzing node stability signatures...", delay_before=1.2),
            TimedMessage(text="🧠 Analyzing ΔPrime vector clusters...", delay_before=2.8),
            TimedMessage(text="📡 Signal drift detected... calibrating...", delay_before=2.4),
            TimedMessage(text="✅ <b>DIAGNOSTIC PHASE 1 COMPLETE.</b>", delay_before=1.8, typing=False),
            TimedMessage(text="<b>ALIGNMENT ANOMALIES DETECTED</b>\n\nYour node trace reveals core-misalignment clusters requiring deeper analysis.", delay_before=2.8),
            TimedMessage(text="🧠 <b>Proceed to Step ②: TRACE_REPORT_Δ7</b> for critical breakdown.", delay_before=2.0),
        ]
        await send_delayed_sequence(context.bot, query.message.chat_id, diagnostic_sequence, initial_delay=0.8)
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.5)
        keyboard_step2 = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ CONTINUE TO STEP ②", callback_data=CALLBACK_S2_FROM_DIAGNOSTIC)]])
        await context.bot.send_message(chat_id=query.message.chat_id, text="Ready to continue?", reply_markup=keyboard_step2, parse_mode=ParseMode.HTML)
        context.user_data["entry_point_s2"] = "from_diagnostic"
        context.user_data["current_flow_step"] = AWAITING_STEP_2_FROM_DIAGNOSTIC
        logger.info(f"[Step ①] User {user_id} completed diagnostic. Status set to: {AWAITING_STEP_2_FROM_DIAGNOSTIC}")
    except Exception as e:
        logger.error(f"Error in s1_initiate_diagnostic_scan_callback for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(query, context, user_id, "An error occurred during diagnostic processing.")


async def s1_view_protocol_overview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        if query: await query.answer()
        return
    user_id = user.id
    context.user_data["user_id"] = user_id
    logger.info(f"[Step ①] BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW}")
    await query.answer()
    try:
        await query.edit_message_text(text="ACTION SELECTED: 📄 VIEW SYSTEM PROTOCOL 📘", reply_markup=None)
        protocol_sequence_text = (
            "📄 <b>System Protocol Overview (Simplified Extract)</b>:\n"
            "<i>All access nodes are subject to periodic stability and alignment checks. "
            "Non-standard signal patterns or deviations from baseline parameters (ΔPrime) "
            "may indicate potential desynchronization risks. Active diagnostic measures are "
            "recommended to ensure continued node viability and prevent automated quarantine protocols.</i>"
        )
        protocol_sequence = [
            TimedMessage(text=protocol_sequence_text, delay_before=1.0),
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
        logger.info(f"[Step ①] User {user_id} viewed protocol. Status: {AWAITING_STEP_2_FROM_PROTOCOL}")
    except Exception as e:
        logger.error(f"Error in s1_view_protocol_overview_callback for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(query, context, user_id, "An error occurred displaying protocol.")


async def s1_ignore_warning_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        if query: await query.answer()
        return
    user_id = user.id
    context.user_data["user_id"] = user_id
    logger.info(f"[Step ①] BUTTON_CLICK: User {user_id} clicked {CALLBACK_S1_IGNORE_WARNING}")
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
        logger.warning(f"[Step ①] User {user_id} ignored warning. Status: {AWAITING_STEP_2_FROM_IGNORE}")
    except Exception as e:
        logger.error(f"Error in s1_ignore_warning_callback for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(query, context, user_id, "An error occurred processing your decision.")


async def step_2_entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        if query: await query.answer("Error: Invalid callback.")
        logger.warning("[Step ① Transition] step_2_entry_handler called with invalid query or user.")
        return

    user_id = user.id
    context.user_data["user_id"] = user_id
    logger.info(f"[Step ① Transition] User {user_id} clicked Step 2 entry button (cb_data: {query.data})")
    await query.answer()
    try:
        source_entry = context.user_data.get("entry_point_s2", "unknown_s2_entry")
        valid_entry_points = {"from_diagnostic", "from_protocol", "from_ignore"}
        if source_entry not in valid_entry_points:
            logger.warning(f"⚠️ User {user_id} attempted invalid Step ② entry point: {source_entry}. current_flow_step: {context.user_data.get('current_flow_step')}")
            await send_system_error_reply(query, context, user_id, "Invalid entry into system diagnostic path. Please restart with /start.")
            context.user_data.pop("current_flow_step", None)
            context.user_data.pop("entry_point_s2", None)
            return

        await query.edit_message_text(
            text="✅ <b>STEP ① COMPLETE — Action Confirmed.</b>\n\n➡️ Proceeding to Step ②...",
            reply_markup=None, parse_mode=ParseMode.HTML
        )
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.0)

        logger.info(f"[Step ① Transition] User {user_id} entering Step 2 from: {source_entry}")
        opening_message_s2_text = ""
        if source_entry == "from_ignore":
            opening_message_s2_text = (
                "⚠️ <b>SYSTEM OVERRIDE PROTOCOL ACTIVE.</b>\n"
                "Your decision to bypass safety checks has been logged.\n"
                "Forced alignment analysis underway via TRACE_REPORT_Δ7."
            )
            context.user_data["risk_score"] = 1.0
        elif source_entry == "from_protocol":
            opening_message_s2_text = (
                "📘 <b>PROTOCOL ACKNOWLEDGED.</b>\n"
                "Your review of system procedures is noted. "
                "Proceeding with standard TRACE_REPORT_Δ7 analysis."
            )
            context.user_data["risk_score"] = 0.5
        else:
            opening_message_s2_text = (
                "🧠 <b>DIAGNOSTIC RESPONSE LOGGED.</b>\n"
                "Launching TRACE_REPORT_Δ7 to trace alignment anomalies found in Phase 1."
            )
            context.user_data["risk_score"] = 0.2

        step2_opening_sequence = [
            TimedMessage(text=opening_message_s2_text, delay_before=1.5),
            TimedMessage(
                text="🧩 <b>STEP ②: TRACE_REPORT_Δ7 ANALYSIS</b> 🧩\n\n"
                     "Scanning ΔPrime vectors...\n"
                     "Correlating signal drift patterns...\n"
                     "Please allow a moment for the system to compile the report.",
                delay_before=1.8
            )
        ]
        await send_delayed_sequence(context.bot, query.message.chat_id, step2_opening_sequence, initial_delay=0.2)
        context.user_data["current_flow_step"] = STEP_2_STARTED_ANALYSIS
        logger.info(f"[Step ① Transition] User {user_id} has started Step 2 analysis. Status: {STEP_2_STARTED_ANALYSIS}, Risk Score: {context.user_data.get('risk_score')}")

        await execute_step_2_scan_sequence(update, context)

    except Exception as e:
        logger.error(f"Error in step_2_entry_handler for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(query, context, user_id, "A system error occurred while proceeding to Step ②.")