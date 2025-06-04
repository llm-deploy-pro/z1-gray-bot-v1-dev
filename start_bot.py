# start_bot.py

import logging
import os
import asyncio

from telegram import Update # Keep for consistency
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters # Added MessageHandler and filters

# --- CRITICAL IMPORT: From handlers.step_1 ---
# Only the main flow function is needed as the button is a URL link
from handlers.step_1 import start_main_unified_flow
# No callback handler or callback data constant needed from step_1.py if URL button is used

# AI_MODIFIED_BLOCK_START: Import the new user input handler
from handlers.user_input_handler import handle_user_text_message
# AI_MODIFIED_BLOCK_END

# --- Environment Variable Logging ---
print(f"CRITICAL_ENV_PRINT_AT_TOP: RENDER_EXTERNAL_URL='{os.environ.get('RENDER_EXTERNAL_URL')}'")
print(f"CRITICAL_ENV_PRINT_AT_TOP: APP_ENV='{os.environ.get('APP_ENV')}'")
print(f"CRITICAL_ENV_PRINT_AT_TOP: PORT='{os.environ.get('PORT')}'")
print(f"CRITICAL_ENV_PRINT_AT_TOP: TELEGRAM_BOT_TOKEN_EXISTS='{'SET' if os.environ.get('TELEGRAM_BOT_TOKEN') else 'NOT_SET'}'")
print(f"CRITICAL_ENV_PRINT_AT_TOP: Z1_GRAY_SALT_EXISTS='{'SET' if os.environ.get('Z1_GRAY_SALT') else 'NOT_SET'}'")

# --- Logging Configuration ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=os.environ.get("LOG_LEVEL", "INFO").upper()
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# --- BOT Configuration ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("FATAL: TELEGRAM_BOT_TOKEN environment variable not set!")
    exit(1)

BOT_VERSION = os.environ.get("BOT_VERSION", "2.2.1-final-perception") # Updated version
APP_ENV = os.environ.get("APP_ENV", "development").lower()
WEBHOOK_URL_BASE_FROM_ENV = os.environ.get("RENDER_EXTERNAL_URL")

# --- Webhook/Polling URL Configuration ---
if APP_ENV == "production":
    if not WEBHOOK_URL_BASE_FROM_ENV:
        logger.critical("FATAL: RENDER_EXTERNAL_URL is MISSING for production on Render!")
        exit(1)
    if not WEBHOOK_URL_BASE_FROM_ENV.startswith("https://"):
        logger.critical(f"FATAL: RENDER_EXTERNAL_URL ('{WEBHOOK_URL_BASE_FROM_ENV}') must be an HTTPS URL!")
        exit(1)
    WEBHOOK_URL_BASE = WEBHOOK_URL_BASE_FROM_ENV
else:
    WEBHOOK_URL_BASE = WEBHOOK_URL_BASE_FROM_ENV if WEBHOOK_URL_BASE_FROM_ENV else "http://localhost.placeholder.for.dev"
    logger.info(f"Development mode. WEBHOOK_URL_BASE (may be placeholder): {WEBHOOK_URL_BASE}")

WEBHOOK_PATH_SEGMENT = "webhook_z1_gray"
logger.info(f"Using webhook path segment: '{WEBHOOK_PATH_SEGMENT}'")
_cleaned_base = WEBHOOK_URL_BASE.rstrip('/')
_cleaned_segment = WEBHOOK_PATH_SEGMENT.lstrip('/')
FULL_WEBHOOK_URL_FOR_TELEGRAM = f"{_cleaned_base}/{_cleaned_segment}" if _cleaned_segment else _cleaned_base

DEFAULT_LOCAL_PORT = 8443
PORT = int(os.environ.get("PORT", os.environ.get("WEBHOOK_PORT", DEFAULT_LOCAL_PORT)))
ALLOWED_UPDATES_TYPES_STR_LIST = ["message", "callback_query"] # Keep callback_query if any other callbacks exist

def main() -> None:
    logger.info(f"--- Starting Z1-Gray Bot (Version: {BOT_VERSION}) ---")
    logger.info(f"Application Environment (APP_ENV): {APP_ENV}")
    logger.info(f"Effective Port for Listener: {PORT}")
    logger.info(f"Bot Token Suffix: ...{BOT_TOKEN[-4:]}")

    application = Application.builder().token(BOT_TOKEN).build()

    # --- Register Handlers ---
    application.add_handler(CommandHandler("start", start_main_unified_flow))
    
    # No CallbackQueryHandler for the main payment button as it's a URL button.
    # If other callback buttons are added in the future, their handlers would be registered here.
    
    logger.info("Registered /start command handler (from handlers.step_1).")

    # AI_MODIFIED_BLOCK_START: Add the new handler for user's free text input
    # This handler will catch any text message that is NOT a command.
    # It's generally good practice to add more general handlers (like this MessageHandler for text)
    # after more specific ones (like CommandHandlers or other specific MessageHandlers/ConversationHandlers).
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_text_message)
    )
    logger.info("Registered user_input_handler for general text messages.")
    # AI_MODIFIED_BLOCK_END
    
    # --- Webhook/Polling Start Logic ---
    try:
        if APP_ENV == "production":
            logger.info(f"Production mode: Initializing webhook application.")
            logger.info(f"  Listener will be on: {os.environ.get('WEBHOOK_LISTEN_IP', '0.0.0.0')}:{PORT}")
            logger.info(f"  Internal URL path for PTB: /{WEBHOOK_PATH_SEGMENT}")
            logger.info(f"  Public Webhook URL for Telegram API: {FULL_WEBHOOK_URL_FOR_TELEGRAM}")
            application.run_webhook(
                listen=os.environ.get("WEBHOOK_LISTEN_IP", "0.0.0.0"),
                port=PORT,
                url_path=WEBHOOK_PATH_SEGMENT,
                webhook_url=FULL_WEBHOOK_URL_FOR_TELEGRAM,
                allowed_updates=ALLOWED_UPDATES_TYPES_STR_LIST,
                drop_pending_updates=True
            )
        else: 
            logger.info(f"Development mode: Initializing polling application.")
            async def _clear_webhook_for_dev(app: Application):
                logger.info("Attempting to clear any existing webhook for development polling...")
                try:
                    await app.bot.delete_webhook(drop_pending_updates=True)
                    logger.info("Webhook cleared successfully for dev polling.")
                except Exception as e_del_wh:
                    logger.warning(f"Could not delete webhook in dev mode (this is often OK): {e_del_wh}")

            try:
                loop = asyncio.get_running_loop()
                asyncio.ensure_future(_clear_webhook_for_dev(application), loop=loop)
            except RuntimeError: 
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_clear_webhook_for_dev(application))
            
            application.run_polling(
                allowed_updates=ALLOWED_UPDATES_TYPES_STR_LIST,
                drop_pending_updates=True
            )
    except Exception as e:
        logger.critical(f"CRITICAL ERROR during bot main execution loop: {e}", exc_info=True)
    finally:
        logger.info(f"--- Z1-Gray Bot (Version: {BOT_VERSION}) application run loop has concluded. ---")

if __name__ == "__main__":
    main()