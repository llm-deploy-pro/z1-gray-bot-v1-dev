# utils/helpers.py

import asyncio
import logging
import datetime
import hashlib
import os
import random
from dataclasses import dataclass, field
from typing import List, Union, Callable, Any, Coroutine, Tuple, Dict

from telegram import Update, CallbackQuery, Message
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError, RetryAfter, TimedOut, NetworkError

logger = logging.getLogger(__name__)

_Z1_GRAY_SALT = os.environ.get("Z1_GRAY_SALT", "DEFAULT_FALLBACK_SALT_CHANGE_ME_XYZ123")
if _Z1_GRAY_SALT == "DEFAULT_FALLBACK_SALT_CHANGE_ME_XYZ123":
    logger.warning("SECURITY WARNING: Using default Z1_GRAY_SALT. Please set a unique Z1_GRAY_SALT environment variable.")

def generate_user_secure_id(user_id: int) -> str:
    """Generates a 16-character uppercase hex string for user ID."""
    # The "USR-" prefix is added by the caller in step_1.py for display purposes.
    # This function returns the raw 16-char hex.
    combined_string = f"RAW_{user_id}_{_Z1_GRAY_SALT}" # Prefix for internal hashing consistency
    hash_object = hashlib.sha256(combined_string.encode('utf-8'))
    return hash_object.hexdigest()[:16].upper()

@dataclass
class TimedMessage:
    text: str
    delay_before: float = 0.8
    typing: bool = True
    parse_mode: Union[str, None] = ParseMode.HTML
    reply_markup: Union[Any, None] = None # For potential inline keyboards in sequence items

async def send_delayed_message(
    bot,
    chat_id: int,
    text: str,
    delay_before: float = 0.8,
    show_typing: bool = True,
    parse_mode: Union[str, None] = ParseMode.HTML,
    reply_markup: Union[Any, None] = None
) -> Union[Message, None]:
    """Helper to send a single message with optional delay and typing."""
    try:
        if show_typing and delay_before > 0.2:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        if delay_before > 0:
            await asyncio.sleep(delay_before)
        message = await bot.send_message(
            chat_id=chat_id, text=text, parse_mode=parse_mode,
            reply_markup=reply_markup, disable_web_page_preview=True
        )
        return message
    except TelegramError as e:
        logger.warning(f"Failed to send single delayed message to chat {chat_id}: '{text[:50]}...' due to {e}")
    except Exception as e_general:
        logger.error(f"Unexpected error sending single delayed message to chat {chat_id}: '{text[:50]}...' due to {e_general}", exc_info=True)
    return None

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
            bot=bot, chat_id=chat_id, text=item.text, delay_before=item.delay_before,
            show_typing=item.typing, parse_mode=item.parse_mode, reply_markup=item.reply_markup
        )
        sent_messages.append(sent_msg)
    return sent_messages

async def send_system_error_reply(
    target_object: Union[Update, CallbackQuery, Message, None],
    context: ContextTypes.DEFAULT_TYPE,
    user_id_param: Union[int, str] = "Unknown",
    error_code: str = "GEN_ERR",
    custom_error_text: Union[str, None] = None
) -> None:
    """Sends a standardized system error reply."""
    default_error_text = "An unexpected system error occurred. Please try the /start sequence again or contact support if the issue persists."
    error_text_to_send = custom_error_text if custom_error_text else default_error_text
    log_user_id_str = str(user_id_param)
    chat_to_send_to = None
    effective_user_telegram_id = None

    if isinstance(target_object, Update):
        if target_object.effective_user:
            effective_user_telegram_id = target_object.effective_user.id
            log_user_id_str = str(effective_user_telegram_id)
        current_message = target_object.effective_message
        if current_message: chat_to_send_to = current_message.chat_id
    elif isinstance(target_object, CallbackQuery):
        if target_object.from_user:
            effective_user_telegram_id = target_object.from_user.id
            log_user_id_str = str(effective_user_telegram_id)
        if target_object.message: chat_to_send_to = target_object.message.chat_id
    elif isinstance(target_object, Message):
        if target_object.from_user:
            effective_user_telegram_id = target_object.from_user.id
            log_user_id_str = str(effective_user_telegram_id)
        chat_to_send_to = target_object.chat_id
    
    if not effective_user_telegram_id and user_id_param == "Unknown" and context.user_data and "user_id" in context.user_data:
        stored_user_id = context.user_data.get("user_id")
        if isinstance(stored_user_id, int):
            effective_user_telegram_id = stored_user_id
            log_user_id_str = str(effective_user_telegram_id)

    logger.error(f"ERROR_CODE: {error_code} - Sending system error reply to user_id='{log_user_id_str}', chat_id='{chat_to_send_to}': {error_text_to_send}")
    final_error_message = (f"⚠️ <b>SYSTEM ERROR (Code: {error_code} / Ref: {log_user_id_str[:8] if log_user_id_str != 'Unknown' else 'N/A'})</b>:\n{error_text_to_send}")

    try:
        reply_candidate = None
        if isinstance(target_object, Update) and target_object.message: reply_candidate = target_object.message
        elif isinstance(target_object, (CallbackQuery, Message)) and getattr(target_object, 'message', None): reply_candidate = getattr(target_object, 'message')
        
        if reply_candidate and hasattr(reply_candidate, 'reply_html'): await reply_candidate.reply_html(final_error_message)
        elif chat_to_send_to and context.bot: await context.bot.send_message(chat_id=chat_to_send_to, text=final_error_message, parse_mode=ParseMode.HTML)
        elif effective_user_telegram_id and context.bot: await context.bot.send_message(chat_id=effective_user_telegram_id, text=final_error_message, parse_mode=ParseMode.HTML)
        else: logger.error(f"Could not send system error reply for {error_code}: No valid target to send message.")
    except RetryAfter as e_retry: logger.warning(f"Rate limited trying to send error reply for {error_code} to user '{log_user_id_str}'. Retry after {e_retry.retry_after}s.")
    except (TimedOut, NetworkError) as e_network: logger.error(f"Network error/timeout sending error reply for {error_code} to user '{log_user_id_str}': {e_network}")
    except TelegramError as e_telegram: logger.error(f"Telegram API error sending error reply for {error_code} to user '{log_user_id_str}': {e_telegram}", exc_info=True)
    except Exception as e_reply_critical: logger.critical(f"CRITICAL: Unhandled exception in send_system_error_reply for {error_code} to user '{log_user_id_str}': {e_reply_critical}", exc_info=True)

def get_display_name(user_obj: Any) -> str: # Parameter name changed for clarity
    """Generates a display name for a user object."""
    if not user_obj: return "Unknown User"
    if hasattr(user_obj, 'full_name') and user_obj.full_name: return user_obj.full_name
    if hasattr(user_obj, 'username') and user_obj.username: return f"@{user_obj.username}"
    if hasattr(user_obj, 'id'): return f"User {user_obj.id}"
    return "User (no identifiable info)"

async def edit_message_safely(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    message_id: int,
    new_text: str,
    new_reply_markup: Union[Any, None] = None,
    parse_mode: Union[str, None] = ParseMode.HTML
) -> bool:
    """Safely attempts to edit a message, handling common errors."""
    try:
        await context.bot.edit_message_text(
            text=new_text, chat_id=chat_id, message_id=message_id,
            reply_markup=new_reply_markup, parse_mode=parse_mode,
            disable_web_page_preview=True
        )
        return True
    except TelegramError as e:
        if "message is not modified" in str(e).lower():
            logger.info(f"Message {message_id} in chat {chat_id} was not modified (already has new content or same as before).")
            return True # State is effectively as desired
        logger.warning(f"Failed to edit message {message_id} in chat {chat_id}: {e}")
        return False
    except Exception as e_general:
        logger.error(f"Unexpected error editing message {message_id} in chat {chat_id}: {e_general}", exc_info=True)
        return False

logger.info("utils.helpers module loaded.")