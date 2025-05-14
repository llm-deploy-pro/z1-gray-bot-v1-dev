# start_bot.py

import logging
import os
import asyncio

from telegram import Update # Not strictly needed here, but often useful
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Import the unified flow handler and its specific callback data
# This line assumes handlers/z1_flow_handler.py exists and contains these names
from handlers.z1_flow_handler import start_z1_gray_unified_flow, handle_unlock_repair_callback_unified, CALLBACK_UNLOCK_REPAIR_49_UNIFIED

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

BOT_VERSION = os.environ.get("BOT_VERSION", "2.0.1-final-unified") # Increment version
APP_ENV = os.environ.get("APP_ENV", "development").lower()
WEBHOOK_URL_BASE_FROM_ENV = os.environ.get("RENDER_EXTERNAL_URL")

# --- Webhook/Polling URL Configuration ---
if APP_ENV == "production":
    if not WEBHOOK_URL_BASE_FROM_ENV:
        logger.critical("FATAL: RENDER_EXTERNAL_URL is MISSING for production on Render! Please set this in your Render service environment.")
        exit(1)
    if not WEBHOOK_URL_BASE_FROM_ENV.startswith("https://"):
        logger.critical(f"FATAL: RENDER_EXTERNAL_URL ('{WEBHOOK_URL_BASE_FROM_ENV}') must be an HTTPS URL for production webhook!")
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
ALLOWED_UPDATES_TYPES_STR_LIST = ["message", "callback_query"]

def main() -> None:
    logger.info(f"--- Starting Z1-Gray Bot (Version: {BOT_VERSION}) ---")
    logger.info(f"Application Environment (APP_ENV): {APP_ENV}")
    logger.info(f"Effective Port for Listener: {PORT}")
    logger.info(f"Bot Token Suffix: ...{BOT_TOKEN[-4:]}")

    application = Application.builder().token(BOT_TOKEN).build()

    # --- Register Handlers for the Unified Flow ---
    application.add_handler(CommandHandler("start", start_z1_gray_unified_flow))
    application.add_handler(CallbackQueryHandler(
        handle_unlock_repair_callback_unified,
        pattern=f"^{CALLBACK_UNLOCK_REPAIR_49_UNIFIED}$"
    ))
    logger.info("Registered unified flow command and callback query handlers.")

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
    # from dotenv import load_dotenv
    # load_dotenv()
    main()