# handlers/z1_flow_handler.py

import asyncio
import logging
import hashlib
import random
from typing import List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError

# Assuming helpers.py contains these:
from utils.helpers import TimedMessage, send_delayed_sequence, generate_user_secure_id, send_system_error_reply

logger = logging.getLogger(__name__)

# --- STATE DEFINITIONS ---
FLOW_ACTIVE_UNIFIED = "z1_flow_unified_active" # General state for the unified flow
FLOW_PAYMENT_BUTTON_SHOWN = "z1_flow_payment_button_shown"
FLOW_PROCESSING_PAYMENT = "z1_flow_processing_payment"
FLOW_PAYMENT_COMPLETE = "z1_flow_payment_complete"

# --- CALLBACK DATA ---
CALLBACK_UNLOCK_REPAIR_49_UNIFIED = "z1_unlock_repair_49_unified"

# --- HELPER FOR IDs (can be moved to utils.helpers if used elsewhere) ---
def _generate_script_id(prefix: str) -> str:
    random_hex = hashlib.sha256(str(random.random()).encode()).hexdigest().upper()
    return f"{prefix}-{random_hex[:8]}"


async def start_z1_gray_unified_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the entire Z1-Gray 3-step script in a unified manner.
    Triggered by /start.
    """
    if not update.message or not update.effective_chat:
        logger.warning("start_z1_gray_unified_flow: Missing message or effective_chat.")
        return

    user = update.effective_user
    if not user:
        logger.warning("start_z1_gray_unified_flow: Effective user is None.")
        await send_system_error_reply(update, context, "UserNotFoundOnUnifiedStart", "User identification failed.")
        return

    user_id = user.id
    chat_id = update.effective_chat.id
    context.user_data["user_id"] = user_id

    current_flow_state = context.user_data.get("current_z1_unified_flow_state")
    active_states_for_reset = [
        FLOW_ACTIVE_UNIFIED, FLOW_PAYMENT_BUTTON_SHOWN, FLOW_PROCESSING_PAYMENT
    ]
    if update.message.text == "/start" and current_flow_state in active_states_for_reset:
        logger.info(f"[Z1 Unified Flow] User {user_id} sent /start mid-flow ({current_flow_state}). Resetting.")
        await update.message.reply_html("🔄 System reset. Re-initiating Z1-Gray protocol...")
        for key in ["current_z1_unified_flow_state", "user_secure_id", "slot_id", "access_key", "z1_payment_message_id"]:
            context.user_data.pop(key, None)
        # Fall through to start fresh

    logger.info(f"[Z1 Unified Flow] User {user_id} (Chat: {chat_id}) starting unified Z1-Gray script.")
    context.user_data["current_z1_unified_flow_state"] = FLOW_ACTIVE_UNIFIED

    # --- 【STEP A】SYSTEM IDENTIFICATION & THREAT ALERT ---
    user_secure_id = generate_user_secure_id(user_id)
    context.user_data["user_secure_id"] = user_secure_id

    messages_step_a = [
        TimedMessage(text="<code>[LOG: Z1_SYS_ALERT_001]</code>\n⚠️📡 <b>[SYSTEM ALERT]</b> Node anomaly detected.", delay_before=0.5),
        TimedMessage(text="<code>[LOG: Z1_SYS_SCAN_002]</code>\n🧬📉 <code>[SCAN COMPLETE]</code> Threat level: <b>HIGH</b>.", delay_before=3.0),
        TimedMessage(text=f"<code>[LOG: Z1_SYS_ID_003]</code>\n🧠🆔 [NODE ID] <b>{user_secure_id}</b>", delay_before=3.0)
    ]

    try:
        msg_object_a = None
        for i, timed_msg in enumerate(messages_step_a):
            if timed_msg.typing and timed_msg.delay_before > 0.2:
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            if timed_msg.delay_before > 0:
                await asyncio.sleep(timed_msg.delay_before)
            if i == 0 and update.message:
                msg_object_a = await update.message.reply_html(text=timed_msg.text)
            else:
                msg_object_a = await context.bot.send_message(chat_id=chat_id, text=timed_msg.text, parse_mode=ParseMode.HTML)
        logger.info(f"[Z1 Unified Flow] User {user_id}: Step A messages sent successfully.")
        await asyncio.sleep(1.5) # Transition delay

        # --- 【STEP B】DIAGNOSTIC REPORT & ACTION MANDATE ---
        slot_id = _generate_script_id("SLT")
        context.user_data["slot_id"] = slot_id

        messages_step_b = [
            TimedMessage(text="<code>[LOG: Z1_SYS_DIAG_004]</code>\n📊🧠 [DIAGNOSTIC REPORT] <i>Critical failure</i> in node integrity.", delay_before=0.5),
            TimedMessage(text="<code>[LOG: Z1_SYS_ACTION_005]</code>\n⚠️🔧 <b>[ACTION REQUIRED]</b> Immediate system intervention mandated.", delay_before=4.0),
            TimedMessage(text=f"<code>[LOG: Z1_SYS_SLOT_006]</code>\n🔒🆔 [SLOT ID] <code>{slot_id}</code>", delay_before=4.0)
        ]
        await send_delayed_sequence(bot=context.bot, chat_id=chat_id, sequence=messages_step_b, initial_delay=0.2)
        logger.info(f"[Z1 Unified Flow] User {user_id}: Step B messages sent successfully.")
        await asyncio.sleep(1.5) # Transition delay

        # --- 【STEP C】LOCK SEQUENCE + ACCESS INITIATION ---
        access_key = _generate_script_id("AKY")
        context.user_data["access_key"] = access_key

        messages_step_c_pre_button = [
            TimedMessage(text=f"<code>[LOG: Z1_SYS_KEY_007]</code>\n🔑⏳ [ACCESS KEY] <b>{access_key}</b>", delay_before=0.5)
        ]
        text_c2_timer = ("<code>[LOG: Z1_SYS_TIMER_008]</code>\n"
                         "⏰⚠️ [TIME REMAINING] <code>08:43 LEFT</code>") # Static timer

        keyboard = [[
            InlineKeyboardButton("🔓 UNLOCK & REPAIR ($49)", callback_data=CALLBACK_UNLOCK_REPAIR_49_UNIFIED)
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if messages_step_c_pre_button:
            await send_delayed_sequence(bot=context.bot, chat_id=chat_id, sequence=messages_step_c_pre_button, initial_delay=0.2)

        if await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING):
            await asyncio.sleep(1.0)
        
        payment_message = await context.bot.send_message(
            chat_id=chat_id,
            text=text_c2_timer,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        context.user_data["z1_payment_message_id"] = payment_message.message_id
        context.user_data["current_z1_unified_flow_state"] = FLOW_PAYMENT_BUTTON_SHOWN
        logger.info(f"[Z1 Unified Flow] User {user_id}: Step C messages and payment button sent. State: {FLOW_PAYMENT_BUTTON_SHOWN}")

    except TelegramError as e:
        logger.error(f"[Z1 Unified Flow] TelegramError for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(update, context, user_id, f"System communication error (Code: TU_COMM_{e.__class__.__name__}). Please try /start again.")
    except Exception as e:
        logger.error(f"[Z1 Unified Flow] General error for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(update, context, user_id, "An unexpected system error occurred (Code: TU_GEN). Please try /start again.")


async def handle_unlock_repair_callback_unified(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the click on "🔓 UNLOCK & REPAIR ($49)" button in the unified flow.
    """
    query = update.callback_query
    user = update.effective_user

    if not query or not user or not query.message:
        logger.warning("[Z1 Unified CB] Invalid callback query or missing user/message.")
        if query: await query.answer("Error processing request.", show_alert=True)
        return

    user_id = user.id
    chat_id = query.message.chat_id
    message_id_to_edit = query.message.message_id

    logger.info(f"[Z1 Unified CB] User {user_id} clicked '{CALLBACK_UNLOCK_REPAIR_49_UNIFIED}'.")

    if context.user_data.get("current_z1_unified_flow_state") != FLOW_PAYMENT_BUTTON_SHOWN:
        logger.warning(f"[Z1 Unified CB] User {user_id} clicked button in unexpected state: {context.user_data.get('current_z1_unified_flow_state')}")
        await query.answer("Request already processed or system is busy. Please wait.", show_alert=True)
        return
    
    context.user_data["current_z1_unified_flow_state"] = FLOW_PROCESSING_PAYMENT

    try:
        await query.answer("Processing...")

        original_text_html = query.message.text_html
        new_text_html = f"{original_text_html}\n\n⏳ <b>Processing...</b>"
        
        await context.bot.edit_message_text(
            text=new_text_html,
            chat_id=chat_id,
            message_id=message_id_to_edit,
            reply_markup=None,
            parse_mode=ParseMode.HTML
        )
        logger.info(f"[Z1 Unified CB] User {user_id}: Payment button message updated to 'Processing...'.")

        await asyncio.sleep(3.0) # Simulate payment verification

        user_secure_id_final = context.user_data.get("user_secure_id", "N/A")
        access_key_final = context.user_data.get("access_key", "N/A")
        
        final_confirmation_text = (
            "<code>[LOG: Z1_SYS_PAYMENT_009_SUCCESS]</code>\n"
            "✅ <b>AUTHORIZATION COMPLETE. PAYMENT RECEIVED.</b>\n\n"
            "Your Z1-GRAY PROTOCOL Access Permission Matrix is now being compiled based on your unique Node ID and Access Key.\n"
            f"Node ID: <code>{user_secure_id_final}</code>\n"
            f"Access Key: <code>{access_key_final}</code>\n\n"
            "➡️ You will receive your personalized Access Matrix documents (the 5 images/files) via a secure direct message or link within the next few minutes.\n\n"
            "<i>Thank you for reactivating your node with Z1-GRAY PROTOCOL.</i>"
        )
        await context.bot.send_message(chat_id=chat_id, text=final_confirmation_text, parse_mode=ParseMode.HTML)
        
        context.user_data["current_z1_unified_flow_state"] = FLOW_PAYMENT_COMPLETE
        logger.info(f"[Z1 Unified CB] User {user_id}: Simulated payment successful. Final message sent. State: {FLOW_PAYMENT_COMPLETE}")

    except TelegramError as te:
        if "message is not modified" in str(te).lower():
            logger.warning(f"[Z1 Unified CB] User {user_id}: Message not modified (already processed). Error: {te}")
        else:
            logger.error(f"[Z1 Unified CB] TelegramError for user {user_id}: {te}", exc_info=True)
            await query.message.reply_text("A communication error occurred. Please contact support.")
            context.user_data["current_z1_unified_flow_state"] = FLOW_PAYMENT_BUTTON_SHOWN # Revert state
    except Exception as e:
        logger.error(f"[Z1 Unified CB] General error for user {user_id}: {e}", exc_info=True)
        await query.message.reply_text("An unexpected error occurred. Please contact support.")
        context.user_data["current_z1_unified_flow_state"] = FLOW_PAYMENT_BUTTON_SHOWN # Revert state