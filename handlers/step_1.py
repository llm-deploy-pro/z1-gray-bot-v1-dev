# handlers/step_1.py (This file now contains the UNIFIED 3-step flow WITH TIMING ADJUSTMENTS)

import asyncio
import logging
import hashlib
import random
from typing import List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from utils.helpers import TimedMessage, send_delayed_sequence, generate_user_secure_id, send_system_error_reply

logger = logging.getLogger(__name__)

# --- STATE DEFINITIONS for the unified flow ---
UNIFIED_FLOW_ACTIVE = "unified_flow_active_s1"
UNIFIED_FLOW_PAYMENT_BUTTON_SHOWN = "unified_flow_payment_button_shown_s1"
UNIFIED_FLOW_PROCESSING_PAYMENT = "unified_flow_processing_payment_s1"
UNIFIED_FLOW_PAYMENT_COMPLETE = "unified_flow_payment_complete_s1"

# --- CALLBACK DATA for the unified flow's payment button ---
CALLBACK_PROCESS_Z1_PAYMENT_FROM_STEP1 = "cb_process_z1_payment_from_step1"

# --- HELPER FOR SCRIPT IDs (specific to this flow if not moved to utils) ---
def _generate_internal_flow_id(prefix: str) -> str:
    """Generates IDs like SLT-XXXXXXXX or AKY-XXXXXXXX for this flow."""
    random_hex = hashlib.sha256(str(random.random()).encode()).hexdigest().upper()
    return f"{prefix.upper()}-{random_hex[:8]}"

# This is the main entry function for the /start command for this flow
async def start_main_unified_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main entry point for the unified Z1-Gray 3-step script, housed in step_1.py.
    Executes STEP A, then STEP B, then STEP C with optimized timing.
    """
    if not update.message or not update.effective_chat:
        logger.warning("start_main_unified_flow: Missing message or effective_chat.")
        return

    user = update.effective_user
    if not user:
        logger.warning("start_main_unified_flow: Effective user is None.")
        await send_system_error_reply(update, context, "UserNotFoundOnUnifiedStartS1", custom_error_text="User identification failed.")
        return

    user_id = user.id
    chat_id = update.effective_chat.id
    context.user_data["user_id"] = user_id

    current_flow_state_key = "current_z1_unified_flow_s1_state"
    current_flow_state = context.user_data.get(current_flow_state_key)

    active_states_for_reset = [
        UNIFIED_FLOW_ACTIVE, UNIFIED_FLOW_PAYMENT_BUTTON_SHOWN, UNIFIED_FLOW_PROCESSING_PAYMENT
    ]
    if update.message.text == "/start" and current_flow_state in active_states_for_reset:
        logger.info(f"[Unified Z1 Flow S1] User {user_id} sent /start mid-flow ({current_flow_state}). Resetting.")
        await update.message.reply_html("🔄 System reset. Re-initiating Z1-Gray protocol...")
        for key in [current_flow_state_key, "user_secure_id_z1_s1", "slot_id_z1_s1", "access_key_z1_s1", "z1_payment_msg_id_s1"]:
            context.user_data.pop(key, None)

    logger.info(f"[Unified Z1 Flow S1] User {user_id} (Chat: {chat_id}) starting unified script from step_1.py with new timing.")
    context.user_data[current_flow_state_key] = UNIFIED_FLOW_ACTIVE

    # --- 【STEP A】SYSTEM IDENTIFICATION & THREAT ALERT (Optimized Timing) ---
    raw_secure_id = generate_user_secure_id(user_id)
    user_secure_id_display = f"USR-{raw_secure_id[:8]}"
    context.user_data["user_secure_id_z1_s1"] = user_secure_id_display

    messages_step_a = [
        TimedMessage(text="<code>[LOG: Z1_SYS_ALERT_001]</code>\n⚠️📡 <b>[SYSTEM ALERT]</b> Node anomaly detected.", delay_before=1.2),   # MODIFIED from 0.5
        TimedMessage(text="<code>[LOG: Z1_SYS_SCAN_002]</code>\n🧬📉 <code>[SCAN COMPLETE]</code> Threat level: <b>HIGH</b>.", delay_before=3.2),   # MODIFIED from 3.0
        TimedMessage(text=f"<code>[LOG: Z1_SYS_ID_003]</code>\n🧠🆔 [NODE ID] <b>{user_secure_id_display}</b>", delay_before=3.2)  # MODIFIED from 3.0
    ]

    try:
        # Send Step A messages
        for i, timed_msg in enumerate(messages_step_a):
            if timed_msg.typing and timed_msg.delay_before > 0.2:
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            if timed_msg.delay_before > 0:
                await asyncio.sleep(timed_msg.delay_before)
            if i == 0 and update.message:
                await update.message.reply_html(text=timed_msg.text)
            else:
                await context.bot.send_message(chat_id=chat_id, text=timed_msg.text, parse_mode=ParseMode.HTML)
        logger.info(f"[Unified Z1 Flow S1] User {user_id}: Step A messages sent (Optimized Timing).")
        # No sleep here, as the last message's delay_before handles the pause before B

        # --- 【STEP B】DIAGNOSTIC REPORT & ACTION MANDATE (Optimized Timing) ---
        # The delay before B starts is now covered by the last delay_before of Step A's messages + send_delayed_sequence's initial_delay if any.
        # Let's ensure a small deliberate pause if the last Step A message had a short delay.
        # Current: Step A last message delay is 3.2s, which is good.
        
        slot_id = _generate_internal_flow_id("SLT")
        context.user_data["slot_id_z1_s1"] = slot_id

        messages_step_b = [
            TimedMessage(text="<code>[LOG: Z1_SYS_DIAG_004]</code>\n📊🧠 [DIAGNOSTIC REPORT] <i>Critical failure</i> in node integrity.", delay_before=1.5),   # MODIFIED from 0.5
            TimedMessage(text="<code>[LOG: Z1_SYS_ACTION_005]</code>\n⚠️🔧 <b>[ACTION REQUIRED]</b> Immediate system intervention mandated.", delay_before=4.5),   # MODIFIED from 4.0
            TimedMessage(text=f"<code>[LOG: Z1_SYS_SLOT_006]</code>\n🔒🆔 [SLOT ID] <code>{slot_id}</code>", delay_before=4.5)  # MODIFIED from 4.0
        ]
        # The send_delayed_sequence function itself has an initial_delay parameter.
        # If we want a pause between Step A completion and Step B start, we can use that,
        # or ensure the first message of Step B has a sufficient delay_before.
        # Here, the first message of Step B has delay_before=1.5s
        await send_delayed_sequence(bot=context.bot, chat_id=chat_id, sequence=messages_step_b, initial_delay=0.2) # Small initial delay for sequence start
        logger.info(f"[Unified Z1 Flow S1] User {user_id}: Step B messages sent (Optimized Timing).")
        # No explicit sleep here, last message of B has delay_before=4.5s

        # --- 【STEP C】LOCK SEQUENCE + ACCESS INITIATION (Optimized Timing) ---
        access_key = _generate_internal_flow_id("AKY")
        context.user_data["access_key_z1_s1"] = access_key

        messages_step_c_pre_button = [
            TimedMessage(text=f"<code>[LOG: Z1_SYS_KEY_007]</code>\n🔑⏳ [ACCESS KEY] <b>{access_key}</b>", delay_before=1.8)   # MODIFIED from 0.5
        ]
        text_c2_timer = ("<code>[LOG: Z1_SYS_TIMER_008]</code>\n"
                         "⏰⚠️ [TIME REMAINING] <code>08:43 LEFT</code>")

        keyboard = [[
            InlineKeyboardButton("🔓 UNLOCK & REPAIR ($49)", callback_data=CALLBACK_PROCESS_Z1_PAYMENT_FROM_STEP1)
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if messages_step_c_pre_button: # Send key message first
            await send_delayed_sequence(bot=context.bot, chat_id=chat_id, sequence=messages_step_c_pre_button, initial_delay=0.2)

        # Send the timer message with the payment button after a longer pause
        if await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING):
            await asyncio.sleep(2.5) # MODIFIED from 1.0 - This is the crucial pause before the button
        
        payment_message = await context.bot.send_message(
            chat_id=chat_id,
            text=text_c2_timer,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        context.user_data["z1_payment_msg_id_s1"] = payment_message.message_id
        context.user_data[current_flow_state_key] = UNIFIED_FLOW_PAYMENT_BUTTON_SHOWN
        logger.info(f"[Unified Z1 Flow S1] User {user_id}: Step C payment button sent (Optimized Timing). State: {UNIFIED_FLOW_PAYMENT_BUTTON_SHOWN}")

    except TelegramError as e:
        logger.error(f"[Unified Z1 Flow S1] TelegramError for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(update, context, user_id, error_code=f"S1_FLOW_TGERR_{e.__class__.__name__}", custom_error_text="A system communication error occurred during the Z1-Gray protocol.")
    except Exception as e:
        logger.error(f"[Unified Z1 Flow S1] General error for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(update, context, user_id, error_code="S1_FLOW_GENERR", custom_error_text="An unexpected error occurred during the Z1-Gray protocol.")

# This is the callback handler for the payment button for this flow
async def handle_unified_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the click on "🔓 UNLOCK & REPAIR ($49)" button from the unified flow in step_1.py.
    """
    query = update.callback_query
    user = update.effective_user
    current_flow_state_key = "current_z1_unified_flow_s1_state"

    if not query or not user or not query.message:
        logger.warning("[Unified Z1 CB S1] Invalid callback query or missing user/message.")
        if query: await query.answer("Error processing request.", show_alert=True)
        return

    user_id = user.id
    chat_id = query.message.chat_id
    message_id_to_edit = query.message.message_id

    logger.info(f"[Unified Z1 CB S1] User {user_id} clicked '{CALLBACK_PROCESS_Z1_PAYMENT_FROM_STEP1}'.")

    if context.user_data.get(current_flow_state_key) != UNIFIED_FLOW_PAYMENT_BUTTON_SHOWN:
        logger.warning(f"[Unified Z1 CB S1] User {user_id} clicked button in unexpected state: {context.user_data.get(current_flow_state_key)}")
        await query.answer()
        return
    
    context.user_data[current_flow_state_key] = UNIFIED_FLOW_PROCESSING_PAYMENT

    try:
        await query.answer("Processing...")

        original_text_html = query.message.text_html
        new_text_html = f"{original_text_html}\n\n⏳ <b>Processing...</b>"
        
        await context.bot.edit_message_text(
            text=new_text_html,
            chat_id=chat_id,
            message_id=message_id_to_edit,
            reply_markup=None, # Remove keyboard
            parse_mode=ParseMode.HTML
        )
        logger.info(f"[Unified Z1 CB S1] User {user_id}: Payment button message updated.")

        await asyncio.sleep(3.0) # Simulate payment verification

        user_secure_id_final = context.user_data.get("user_secure_id_z1_s1", "N/A")
        access_key_final = context.user_data.get("access_key_z1_s1", "N/A")
        
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
        
        context.user_data[current_flow_state_key] = UNIFIED_FLOW_PAYMENT_COMPLETE
        logger.info(f"[Unified Z1 CB S1] User {user_id}: Simulated payment successful. State: {UNIFIED_FLOW_PAYMENT_COMPLETE}")

    except TelegramError as te:
        if "message is not modified" in str(te).lower():
            logger.warning(f"[Unified Z1 CB S1] User {user_id}: Message not modified (already processed). Error: {te}")
        else:
            logger.error(f"[Unified Z1 CB S1] TelegramError for user {user_id}: {te}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text="A communication error occurred processing your request. Please contact support.", parse_mode=ParseMode.HTML)
            context.user_data[current_flow_state_key] = UNIFIED_FLOW_PAYMENT_BUTTON_SHOWN
    except Exception as e:
        logger.error(f"[Unified Z1 CB S1] General error for user {user_id}: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="An unexpected error occurred. Please contact support.", parse_mode=ParseMode.HTML)
        context.user_data[current_flow_state_key] = UNIFIED_FLOW_PAYMENT_BUTTON_SHOWN

logger.info("handlers.step_1 (containing unified Z1-Gray flow with optimized timing) module loaded.")