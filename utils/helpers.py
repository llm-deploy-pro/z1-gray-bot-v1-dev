import asyncio
import logging
import datetime
import hashlib
import os # Added for os.environ.get
from dataclasses import dataclass
from typing import List, Union

from telegram import Update, CallbackQuery
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

_Z1_GRAY_SALT = os.environ.get("Z1_GRAY_SALT", "DEFAULT_FALLBACK_SALT_CHANGE_ME_XYZ123")
if _Z1_GRAY_SALT == "DEFAULT_FALLBACK_SALT_CHANGE_ME_XYZ123":
    logger.warning("SECURITY WARNING: Using default Z1_GRAY_SALT. Please set a unique Z1_GRAY_SALT environment variable.")

def generate_user_secure_id(user_id: int) -> str:
    combined_string = f"{user_id}_{_Z1_GRAY_SALT}"
    hash_object = hashlib.sha256(combined_string.encode('utf-8'))
    return hash_object.hexdigest()[:16]

@dataclass
class TimedMessage:
    text: str
    delay_before: float = 0.8
    typing: bool = True
    # Optional: Add a field for a minimal system log to be appended
    system_log: Union[str, None] = None

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
        system_log_to_append = item.system_log

        if show_typing and delay_before_send > 0.2:
            try:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except TelegramError as e_chat_action:
                logger.warning(f"Failed to send chat action in chat {chat_id}: {e_chat_action}")

        if delay_before_send > 0:
            await asyncio.sleep(delay_before_send)

        message_content = text_to_send
        if system_log_to_append:
            # Append system log with a newline and as code for distinction
            message_content += f"\n<code>{system_log_to_append}</code>"

        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message_content, # Use the combined content
                parse_mode=ParseMode.HTML
            )
        except TelegramError as e_send:
            logger.warning(f"Failed to send message in sequence to chat {chat_id}: '{item.text[:30]}...' due to {e_send}")
        except Exception as e_general:
            logger.error(f"Unexpected error sending message in sequence to chat {chat_id}: '{item.text[:30]}...' due to {e_general}", exc_info=True)

async def send_system_error_reply(
    target_object: Union[Update, CallbackQuery, None],
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int | str = "Unknown",
    error_text: str = "An unexpected system error occurred. Please try the /start sequence again or contact support if the issue persists."
) -> None:
    logger.error(f"Sending system error reply to user {user_id}: {error_text}")
    try:
        reply_target_message = None
        if isinstance(target_object, Update) and target_object.message:
            reply_target_message = target_object.message
            if user_id == "Unknown" and target_object.effective_user:
                 user_id = target_object.effective_user.id
        elif isinstance(target_object, CallbackQuery) and target_object.message:
            reply_target_message = target_object.message
            if user_id == "Unknown" and target_object.effective_user:
                 user_id = target_object.effective_user.id
        elif user_id == "Unknown" and context.user_data and "user_id" in context.user_data:
            user_id = context.user_data["user_id"]

        if reply_target_message and hasattr(reply_target_message, 'reply_html'):
             await reply_target_message.reply_html(f"⚠️ <b>SYSTEM ERROR:</b>\n{error_text}")
        elif user_id != "Unknown" and context.bot:
            await context.bot.send_message(chat_id=user_id, text=f"⚠️ <b>SYSTEM ERROR:</b>\n{error_text}", parse_mode=ParseMode.HTML)
        else:
            logger.error(f"Could not send system error reply: No valid target_object or user_id. Error: {error_text}")
    except Exception as e_reply:
        logger.error(f"CRITICAL: Failed to send system error reply to user {user_id}: {e_reply}")