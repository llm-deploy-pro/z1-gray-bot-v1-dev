# utils/helpers.py

import asyncio
import logging
import datetime
import hashlib
import os
import random
from dataclasses import dataclass, field # field might not be used here but often imported
from typing import List, Union, Callable, Any, Coroutine, Tuple, Dict # Added more common types

from telegram import Update, CallbackQuery, Message # For type hinting
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError, RetryAfter, TimedOut, NetworkError # Specific errors

logger = logging.getLogger(__name__)

# --- Environment Variables & Constants ---
_Z1_GRAY_SALT = os.environ.get("Z1_GRAY_SALT", "DEFAULT_FALLBACK_SALT_CHANGE_ME_XYZ123")
if _Z1_GRAY_SALT == "DEFAULT_FALLBACK_SALT_CHANGE_ME_XYZ123":
    logger.warning("SECURITY WARNING: Using default Z1_GRAY_SALT. Please set a unique Z1_GRAY_SALT environment variable.")

# --- ID Generation ---
def generate_user_secure_id(user_id: int) -> str:
    """
    Generates a 16-character uppercase hex string based on Telegram user_id and salt.
    This is the raw ID. The "USR-" prefix for display is added by the caller.
    """
    # Using a prefix in the hash input for better salt mixing, even if not strictly necessary for this case
    combined_string = f"Z1_USER_ID_RAW_{user_id}_{_Z1_GRAY_SALT}"
    hash_object = hashlib.sha256(combined_string.encode('utf-8'))
    return hash_object.hexdigest()[:16].upper()

# Note: _generate_internal_flow_id was kept in handlers/step_1.py as it was specific to that flow's needs.
# If it were more general, it could be moved here.

# --- Message Sequencing & Sending ---
@dataclass
class TimedMessage: # This dataclass is now less used as step_1.py sends messages individually for fine ChatAction control
    text: str
    delay_before: float = 0.8
    typing: bool = True
    parse_mode: Union[str, None] = ParseMode.HTML
    reply_markup: Union[Any, None] = None

async def send_delayed_message(
    bot, # Typically context.bot
    chat_id: int,
    text: str,
    delay_before: float = 0.0, # Default to 0 if external sleep is primary
    show_typing: bool = True, # Can be overridden by caller
    parse_mode: Union[str, None] = ParseMode.HTML,
    reply_markup: Union[Any, None] = None,
    disable_web_page_preview: bool = True # Good default for system messages
) -> Union[Message, None]:
    """
    Helper to send a single message with optional delay and typing.
    The `delay_before` here is AFTER any externally controlled ChatAction delays.
    """
    try:
        if show_typing and delay_before > 0.2: # Only show typing if there's a noticeable delay *for this message*
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        if delay_before > 0:
            await asyncio.sleep(delay_before)

        message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview
        )
        return message
    except TelegramError as e:
        logger.warning(f"Failed to send single delayed message to chat {chat_id}: '{text[:70]}...' due to {e}")
    except Exception as e_general:
        logger.error(f"Unexpected error sending single delayed message to chat {chat_id}: '{text[:70]}...' due to {e_general}", exc_info=True)
    return None

# send_delayed_sequence is kept for potential future use or other parts of the bot,
# but the main Z1-Gray flow in step_1.py now sends messages individually for precise ChatAction control.
async def send_delayed_sequence(
    bot,
    chat_id: int,
    sequence: List[TimedMessage],
    initial_delay: float = 0
) -> List[Union[Message, None]]:
    """Sends a sequence of TimedMessage objects."""
    sent_messages: List[Union[Message, None]] = []
    if initial_delay > 0:
        await asyncio.sleep(initial_delay)

    for item in sequence:
        sent_msg = await send_delayed_message(
            bot=bot,
            chat_id=chat_id,
            text=item.text,
            delay_before=item.delay_before,
            show_typing=item.typing,
            parse_mode=item.parse_mode,
            reply_markup=item.reply_markup
        )
        sent_messages.append(sent_msg)
    return sent_messages

# --- Error Handling ---
async def send_system_error_reply(
    target_object: Union[Update, CallbackQuery, Message, None],
    context: ContextTypes.DEFAULT_TYPE,
    user_id_param: Union[int, str] = "Unknown", # Parameter name to avoid conflict
    error_code: str = "SYS_ERR_GEN", # More specific default error code
    custom_error_text: Union[str, None] = None
) -> None:
    """Sends a standardized system error reply to the user."""
    default_error_text = "An unexpected system error occurred. Please try the /start sequence again or contact support if the issue persists."
    error_text_to_send = custom_error_text if custom_error_text else default_error_text

    log_user_id_str = str(user_id_param)
    chat_to_send_to = None
    effective_user_telegram_id = None # Will hold the actual Telegram user ID

    # Attempt to extract user_id and chat_id from the target_object
    if isinstance(target_object, Update):
        if target_object.effective_user:
            effective_user_telegram_id = target_object.effective_user.id
        current_message = target_object.effective_message # Handles both direct message and callback_query.message
        if current_message:
            chat_to_send_to = current_message.chat_id
            if not effective_user_telegram_id and current_message.from_user: # Ensure we get user_id from message if not from effective_user
                effective_user_telegram_id = current_message.from_user.id
    elif isinstance(target_object, CallbackQuery):
        if target_object.from_user:
            effective_user_telegram_id = target_object.from_user.id
        if target_object.message:
            chat_to_send_to = target_object.message.chat_id
    elif isinstance(target_object, Message):
        if target_object.from_user:
            effective_user_telegram_id = target_object.from_user.id
        chat_to_send_to = target_object.chat_id
    
    # Update log_user_id_str if we found a more specific effective_user_telegram_id
    if effective_user_telegram_id:
        log_user_id_str = str(effective_user_telegram_id)
    # Fallback from context.user_data if still "Unknown" and context has it
    elif log_user_id_str == "Unknown" and context.user_data and "user_id" in context.user_data:
        stored_user_id = context.user_data.get("user_id")
        if isinstance(stored_user_id, int): # Ensure it's a valid ID type
            effective_user_telegram_id = stored_user_id
            log_user_id_str = str(effective_user_telegram_id)

    logger.error(
        f"ERROR_CODE: {error_code} - Sending system error reply to user_id='{log_user_id_str}', "
        f"chat_id='{chat_to_send_to}': {error_text_to_send}"
    )

    final_error_message = (
        f"⚠️ <b>SYSTEM ERROR (Code: {error_code} / Ref: {log_user_id_str[:8] if log_user_id_str != 'Unknown' else 'N/A'})</b>:\n"
        f"{error_text_to_send}"
    )

    try:
        # Determine the best way to reply or send the message
        reply_candidate = None
        if isinstance(target_object, Update) and target_object.message:
            reply_candidate = target_object.message
        elif isinstance(target_object, CallbackQuery) and target_object.message:
            reply_candidate = target_object.message
        elif isinstance(target_object, Message):
            reply_candidate = target_object
        
        if reply_candidate and hasattr(reply_candidate, 'reply_html'):
            await reply_candidate.reply_html(final_error_message)
        elif chat_to_send_to and context.bot: # If we have a chat_id (e.g. from callback without direct message access)
            await context.bot.send_message(chat_id=chat_to_send_to, text=final_error_message, parse_mode=ParseMode.HTML)
        elif effective_user_telegram_id and context.bot: # Fallback to PMing the user if only their Telegram ID is known
            await context.bot.send_message(chat_id=effective_user_telegram_id, text=final_error_message, parse_mode=ParseMode.HTML)
        else:
            logger.error(f"Could not send system error reply for {error_code}: No valid target (chat_id or user_id) to send the message.")
            
    except RetryAfter as e_retry:
        logger.warning(f"Rate limited trying to send error reply for {error_code} to user '{log_user_id_str}'. Retry after {e_retry.retry_after}s.")
    except (TimedOut, NetworkError) as e_network:
        logger.error(f"Network error/timeout sending error reply for {error_code} to user '{log_user_id_str}': {e_network}")
    except TelegramError as e_telegram:
        logger.error(f"Telegram API error sending error reply for {error_code} to user '{log_user_id_str}': {e_telegram}", exc_info=True)
    except Exception as e_reply_critical:
        logger.critical(f"CRITICAL: Unhandled exception in send_system_error_reply for {error_code} to user '{log_user_id_str}': {e_reply_critical}", exc_info=True)

# --- Other Utility Functions ---
def get_display_name(user_obj: Any) -> str:
    """Generates a display name for a user object, preferring full name."""
    if not user_obj:
        return "Unknown User"
    if hasattr(user_obj, 'full_name') and user_obj.full_name:
        return user_obj.full_name
    if hasattr(user_obj, 'username') and user_obj.username:
        return f"@{user_obj.username}"
    # Fallback to ID if available
    if hasattr(user_obj, 'id'):
        return f"User {user_obj.id}"
    return "User (no identifiable info)"

async def edit_message_safely(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    message_id: int,
    new_text: str,
    new_reply_markup: Union[Any, None] = None,
    parse_mode: Union[str, None] = ParseMode.HTML,
    disable_web_page_preview: bool = True
) -> bool:
    """Safely attempts to edit a message, handling common errors like 'message is not modified'."""
    try:
        await context.bot.edit_message_text(
            text=new_text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=new_reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
        return True
    except TelegramError as e:
        if "message is not modified" in str(e).lower():
            logger.info(f"Message {message_id} in chat {chat_id} was not modified (already has new content or same as before).")
            return True # Operation is idempotent in this case, state is as desired.
        logger.warning(f"Failed to edit message {message_id} in chat {chat_id}: {e}")
        return False
    except Exception as e_general:
        logger.error(f"Unexpected error editing message {message_id} in chat {chat_id}: {e_general}", exc_info=True)
        return False

logger.info("utils.helpers module loaded successfully.")