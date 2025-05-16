# handlers/step_1.py (This file now contains the UNIFIED 3-step flow WITH TIMING ADJUSTMENTS and FINAL ENHANCEMENTS)

import asyncio
import logging
import hashlib
import random
from typing import List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from utils.helpers import TimedMessage, send_delayed_message, generate_user_secure_id, send_system_error_reply

logger = logging.getLogger(__name__)

# --- STATE DEFINITIONS for the unified flow ---
UNIFIED_FLOW_ACTIVE = "unified_flow_active_s1_v3" # Versioning state names
UNIFIED_FLOW_PAYMENT_LINK_SENT = "unified_flow_payment_link_sent_s1_v3"
# No processing/complete states needed here as it's a URL button

# --- HELPER FOR SCRIPT IDs ---
def _generate_internal_flow_id(prefix: str, length: int = 8) -> str:
    random_hex = hashlib.sha256(str(random.random()).encode()).hexdigest().upper()
    return f"{prefix.upper()}-{random_hex[:length]}"

# --- Constants for dynamic content generation ---
INTEGRITY_MIN = 24.5
INTEGRITY_MAX = 49.5
SEED_MAX_VAL = 65535

async def start_main_unified_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        logger.warning("start_main_unified_flow: Missing message or effective_chat.")
        return

    user = update.effective_user
    if not user:
        logger.warning("start_main_unified_flow: Effective user is None.")
        await send_system_error_reply(update, context, "UserNotFoundS1V3", custom_error_text="User identification failed.")
        return

    user_id = user.id
    chat_id = update.effective_chat.id
    context.user_data["user_id"] = user_id

    current_flow_state_key = "current_z1_unified_flow_s1_v3_state" # Unique state key
    current_flow_state = context.user_data.get(current_flow_state_key)

    active_states_for_reset = [UNIFIED_FLOW_ACTIVE, UNIFIED_FLOW_PAYMENT_LINK_SENT]
    if update.message.text == "/start" and current_flow_state in active_states_for_reset:
        logger.info(f"[Unified Z1 Flow S1 V3] User {user_id} sent /start mid-flow ({current_flow_state}). Resetting.")
        await update.message.reply_html("🔄 System reset. Re-initiating Z1-Gray protocol...")
        keys_to_clear = [
            current_flow_state_key, "user_secure_id_z1_s1_v3", "slot_id_z1_s1_v3", 
            "access_key_z1_s1_v3", "integrity_value_s1_v3", "sync_seed_s1_v3", 
            "node_echo_id_s1_v3", "checksum_val_s1_v3" # Ensured all relevant keys are listed
        ]
        for key in keys_to_clear:
            context.user_data.pop(key, None)

    logger.info(f"[Unified Z1 Flow S1 V3] User {user_id} (Chat: {chat_id}) starting script with final button optimizations.")
    context.user_data[current_flow_state_key] = UNIFIED_FLOW_ACTIVE

    try:
        # --- 【STEP A】SYSTEM IDENTIFICATION & THREAT ALERT ---
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
        await asyncio.sleep(0.3)
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        text_a1 = "<code>[LOG: Z1_SYS_ALERT_001]</code>\n🟥🟥🟧⬜⬜ <b>[SYSTEM ALERT]</b> Node anomaly detected."
        msg_delay_a1 = 1.2 - 0.3
        if update.message:
            await send_delayed_message(context.bot, chat_id, text_a1, context=context, delay_before=msg_delay_a1, show_typing=False) # Pass context
        else:
            await send_delayed_message(context.bot, chat_id, text_a1, context=context, delay_before=msg_delay_a1, show_typing=False) # Pass context

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
        await asyncio.sleep(1.2)
        text_a2 = "<code>[LOG: Z1_SYS_SCAN_002]</code>\n🧬📉 <code>[SCAN COMPLETE]</code> Threat level: <b>HIGH</b>."
        msg_delay_a2 = 3.2 - 1.2
        await send_delayed_message(context.bot, chat_id, text_a2, context=context, delay_before=msg_delay_a2, show_typing=True) # Pass context

        raw_secure_id = generate_user_secure_id(user_id)
        user_secure_id_display = f"USR-{raw_secure_id[:8]}"
        context.user_data["user_secure_id_z1_s1_v3"] = user_secure_id_display
        text_a3 = f"<code>[LOG: Z1_SYS_ID_003]</code>\n🧠🆔 [NODE ID] <b>{user_secure_id_display}</b>"
        await send_delayed_message(context.bot, chat_id, text_a3, context=context, delay_before=3.2, show_typing=True) # Pass context
        logger.info(f"[Unified Z1 Flow S1 V3] User {user_id}: Step A messages sent.")

        # --- 【STEP B】DIAGNOSTIC REPORT & ACTION MANDATE ---
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
        await asyncio.sleep(1.3)
        integrity_val = round(random.uniform(INTEGRITY_MIN, INTEGRITY_MAX), 1)
        context.user_data["integrity_value_s1_v3"] = integrity_val
        text_b1 = (f"<code>[LOG: Z1_SYS_DIAG_004]</code>\n"
                   f"📊🧠 [DIAGNOSTIC REPORT] <i>Critical failure</i> in node integrity.\n"
                   f"<b>Status:</b> 🟥🟥🟥🟥🟧 (Integrity: <code>{integrity_val}%</code>)")
        msg_delay_b1 = 1.5 - 1.3
        await send_delayed_message(context.bot, chat_id, text_b1, context=context, delay_before=msg_delay_b1, show_typing=True) # Pass context

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO_NOTE)
        await asyncio.sleep(1.2)
        slot_id = _generate_internal_flow_id("SLT")
        context.user_data["slot_id_z1_s1_v3"] = slot_id
        text_b2 = (f"<code>[LOG: Z1_SYS_ACTION_005]</code>\n"
                   f"⚠️🔧 <b>[ACTION REQUIRED]</b> Immediate system intervention mandated.\n"
                   f"<i>System override: SLOT [<code>{slot_id}</code>] secured for immediate recalibration.</i>")
        msg_delay_b2 = 4.5 - 1.2
        await send_delayed_message(context.bot, chat_id, text_b2, context=context, delay_before=msg_delay_b2, show_typing=True) # Pass context
        
        node_echo_id = format(random.randint(0, SEED_MAX_VAL), '04X')
        context.user_data["node_echo_id_s1_v3"] = node_echo_id
        text_b2_echo = (f"<code>[SYS NODE AI::echo]</code> Node stabilization task [#{node_echo_id}] acknowledged.")
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await send_delayed_message(context.bot, chat_id, text_b2_echo, context=context, delay_before=1.0, show_typing=False) # Pass context

        text_b3 = f"<code>[LOG: Z1_SYS_SLOT_006]</code>\n🔒🆔 [SLOT ID] <code>{slot_id}</code>"
        await send_delayed_message(context.bot, chat_id, text_b3, context=context, delay_before=2.0, show_typing=True) # Pass context
        logger.info(f"[Unified Z1 Flow S1 V3] User {user_id}: Step B messages (with AI echo) sent.")

        # --- 【STEP C】LOCK SEQUENCE + ACCESS INITIATION ---
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
        await asyncio.sleep(1.2)
        access_key = _generate_internal_flow_id("AKY")
        context.user_data["access_key_z1_s1_v3"] = access_key
        sync_seed_val = format(random.randint(0, SEED_MAX_VAL), '04X')
        context.user_data["sync_seed_s1_v3"] = sync_seed_val
        checksum_val = format(random.randint(0, SEED_MAX_VAL), '04X')
        context.user_data["checksum_val_s1_v3"] = checksum_val
        text_c1 = (
            f"<code>[LOG: Z1_SYS_KEY_007]</code>\n"
            f"🔐 Root Protocol: SYNC_SEED::<code>{sync_seed_val}</code> (checksum:<code>{checksum_val}</code>) → <b>KEY DERIVED</b>\n"
            f"🔑⏳ [ACCESS KEY] <b>{access_key}</b>\n"
            f"KEY validation sequence initiated: <b>[Phase 1/3 Complete]</b>"
        )
        msg_delay_c1 = 1.8 - 1.2
        await send_delayed_message(context.bot, chat_id, text_c1, context=context, delay_before=msg_delay_c1, show_typing=True) # Pass context

        text_c2_with_button = (
            f"<b>⚠️ Activation Slot Reserved</b>\n"
            f"Only <code>1</code> access slot remains for your Node ID.\n\n"
            f"<code>[LOG: Z1_SYS_TIMER_008]</code>\n"
            f"⏰⚠️ [TIME REMAINING] <code>08:43 LEFT</code>\n\n"
            f"<b>Note:</b> Action cannot be reversed once initiated.\n\n"
            f"<i>Clicking below will open a secure payment portal for your activation.</i>"
        )
        gumroad_url = "https://syncprotocol.gumroad.com/l/ENTRY_SYNC_49"
        keyboard_c2 = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔗 ENTER SECURE PORTAL – $49", url=gumroad_url)
        ]])

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(2.5)
        
        # No need to pass context to context.bot.send_message directly
        await context.bot.send_message(
            chat_id=chat_id,
            text=text_c2_with_button,
            reply_markup=keyboard_c2,
            parse_mode=ParseMode.HTML
        )
        context.user_data[current_flow_state_key] = UNIFIED_FLOW_PAYMENT_LINK_SENT
        logger.info(f"[Unified Z1 Flow S1 V3] User {user_id}: Step C payment URL button sent.")

        await asyncio.sleep(2.8) 
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(1.0)
        text_gateway_confirmation_msg = (
            "<code>[LOG: Z1_SYS_GATEWAY_009]</code>\n"
            "✅ <b>Link confirmed</b>. Finalizing your session on the secure gateway...\n"
            "Please complete the process on the opened page."
        )
        # No need to pass context to context.bot.send_message directly
        await context.bot.send_message(chat_id=chat_id, text=text_gateway_confirmation_msg, parse_mode=ParseMode.HTML)
        logger.info(f"[Unified Z1 Flow S1 V3] User {user_id}: Sent 'Link confirmed' gateway message.")

    except TelegramError as e:
        logger.error(f"[Unified Z1 Flow S1 V3] TelegramError for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(update, context, user_id, error_code=f"S1V3_TGERR_{e.__class__.__name__}", custom_error_text="A system communication error occurred.")
    except Exception as e:
        logger.error(f"[Unified Z1 Flow S1 V3] General error for user {user_id}: {e}", exc_info=True)
        await send_system_error_reply(update, context, user_id, error_code="S1V3_GENERR", custom_error_text="An unexpected error occurred.")

# --- Function to handle unexpected user text input during the flow ---
async def handle_unexpected_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        logger.warning("handle_unexpected_input: Received update without crucial attributes.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text_received = update.message.text
    logger.info(f"[Unexpected Input] User {user_id} in chat {chat_id} sent text during flow: '{text_received[:50]}'")

    current_flow_state_key = "current_z1_unified_flow_s1_v3_state"
    current_state = context.user_data.get(current_flow_state_key)

    valid_interrupt_states = [
        UNIFIED_FLOW_ACTIVE,
        UNIFIED_FLOW_PAYMENT_LINK_SENT
    ]

    if current_state not in valid_interrupt_states:
        logger.info(f"[Unexpected Input] User {user_id} sent text but not in an active Z1-Gray flow state ({current_state}). Ignoring.")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(0.8) 

    reply_text_html = (
        "<code>[LOG: Z1_ECHO_MON]</code> 🧠 External signal received.<br>"
        "<b>Manual input logged. Processing will resume once current protocol completes.</b>"
    )
    # No need to pass context to context.bot.send_message directly
    await context.bot.send_message(
        chat_id=chat_id,
        text=reply_text_html,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    logger.info(f"[Unexpected Input] Sent Z1_ECHO_MON reply to user {user_id}.")

    disruption_delay_seconds = 3.0
    context.user_data["input_disruption_delay_s"] = disruption_delay_seconds # Key for disruption delay
    logger.info(f"[Unexpected Input] Set input_disruption_delay_s to {disruption_delay_seconds}s for user {user_id}.")


logger.info("handlers.step_1 (unified flow v3 with final enhancements and input handling) module loaded.")