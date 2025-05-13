# start_bot.py (Simplified Webhook Path for Debugging)

import logging
import os
import asyncio
import hashlib # Still imported, though hash might not be used in this test

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from handlers import step_1

# --- CRITICAL ENVIRONMENT VARIABLE CHECK AT THE VERY TOP ---
logger_env_debug = logging.getLogger("ENV_DEBUG_VERY_TOP")
# Ensure logging is configured to capture this, or use print for absolute certainty in Render logs
# Forcing print here for maximum visibility in Render logs if logging isn't fully set up yet:
print(f"CRITICAL_ENV_PRINT_AT_TOP: RENDER_EXTERNAL_URL='{os.environ.get('RENDER_EXTERNAL_URL')}'")
print(f"CRITICAL_ENV_PRINT_AT_TOP: APP_ENV='{os.environ.get('APP_ENV')}'")
print(f"CRITICAL_ENV_PRINT_AT_TOP: PORT='{os.environ.get('PORT')}'")
print(f"CRITICAL_ENV_PRINT_AT_TOP: TELEGRAM_BOT_TOKEN_EXISTS='{'SET' if os.environ.get('TELEGRAM_BOT_TOKEN') else 'NOT_SET'}'")
# --- END OF CRITICAL ENV CHECK ---


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=os.environ.get("LOG_LEVEL", "INFO").upper()
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("FATAL: TELEGRAM_BOT_TOKEN environment variable not set!")
    exit(1)

APP_ENV = os.environ.get("APP_ENV", "development").lower()
WEBHOOK_URL_BASE_FROM_ENV = os.environ.get("RENDER_EXTERNAL_URL")

if APP_ENV == "production":
    if not WEBHOOK_URL_BASE_FROM_ENV:
        logger.critical("FATAL: RENDER_EXTERNAL_URL is MISSING for production on Render!")
        exit(1)
    if not WEBHOOK_URL_BASE_FROM_ENV.startswith("https://"):
        logger.critical(f"FATAL: RENDER_EXTERNAL_URL ('{WEBHOOK_URL_BASE_FROM_ENV}') is NOT an HTTPS URL for production!")
        exit(1)
    WEBHOOK_URL_BASE = WEBHOOK_URL_BASE_FROM_ENV
else: # Development
    WEBHOOK_URL_BASE = WEBHOOK_URL_BASE_FROM_ENV if WEBHOOK_URL_BASE_FROM_ENV else "http://localhost.placeholder.dev"
    logger.info(f"Development mode. WEBHOOK_URL_BASE resolved to: {WEBHOOK_URL_BASE}")

# --- MODIFICATION FOR DEBUGGING: SIMPLIFIED WEBHOOK PATH ---
WEBHOOK_PATH_SEGMENT = "" # Set to empty string for testing root path
logger.info(f"DEBUGGING: Using EMPTY webhook path segment: '{WEBHOOK_PATH_SEGMENT}'")
FULL_WEBHOOK_URL_FOR_TELEGRAM = WEBHOOK_URL_BASE.rstrip('/') # No path segment added
# --- END OF MODIFICATION ---

PORT = int(os.environ.get("PORT", os.environ.get("WEBHOOK_PORT", 8443)))
ALLOWED_UPDATES_TYPES_STR_LIST = ["message", "callback_query"]


def main() -> None:
    logger.info(f"--- Starting Z1-Gray Bot (DEBUGGING WEBHOOK PATH) ---")
    logger.info(f"Final APP_ENV: {APP_ENV}")
    logger.info(f"Final PORT: {PORT}")
    logger.info(f"Final WEBHOOK_URL_BASE for logic: {WEBHOOK_URL_BASE}")
    logger.info(f"Final FULL_WEBHOOK_URL_FOR_TELEGRAM (Simplified): {FULL_WEBHOOK_URL_FOR_TELEGRAM}")
    logger.info(f"Final WEBHOOK_PATH_SEGMENT for run_webhook (Simplified): '{WEBHOOK_PATH_SEGMENT}'")
    logger.info(f"Bot Token: ...{BOT_TOKEN[-4:]}")

    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", step_1.start_step_1_flow))
    application.add_handler(CallbackQueryHandler(step_1.s1_initiate_diagnostic_scan_callback, pattern=f"^{step_1.CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN}$"))
    application.add_handler(CallbackQueryHandler(step_1.s1_view_protocol_overview_callback, pattern=f"^{step_1.CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW}$"))
    application.add_handler(CallbackQueryHandler(step_1.s1_ignore_warning_callback, pattern=f"^{step_1.CALLBACK_S1_IGNORE_WARNING}$"))
    application.add_handler(CallbackQueryHandler(step_1.step_2_entry_handler, pattern=r"^step2_entry_from_.*$"))
    logger.info("Registered command and callback query handlers.")

    try:
        if APP_ENV == "production":
            logger.info(f"Production mode: Calling application.run_webhook() with simplified path.")
            logger.info(
                f"  To manually verify (if issues persist):\n"
                f"  curl -F \"url={FULL_WEBHOOK_URL_FOR_TELEGRAM}\" -F \"allowed_updates={ALLOWED_UPDATES_TYPES_STR_LIST}\" https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
            )
            application.run_webhook(
                listen=os.environ.get("WEBHOOK_LISTEN_IP", "0.0.0.0"),
                port=PORT,
                url_path=WEBHOOK_PATH_SEGMENT, # Now an empty string
                webhook_url=FULL_WEBHOOK_URL_FOR_TELEGRAM,
                allowed_updates=ALLOWED_UPDATES_TYPES_STR_LIST,
                drop_pending_updates=True
            )
        else: # Development
            logger.info(f"Development mode: Clearing webhook and starting polling.")
            async def _delete_webhook_dev():
                try:
                    await application.bot.delete_webhook(drop_pending_updates=True)
                    logger.info("Webhook cleared for dev polling.")
                except Exception as e_del:
                    logger.warning(f"Could not delete webhook in dev (normal if none set): {e_del}")
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running(): asyncio.ensure_future(_delete_webhook_dev())
                else: loop.run_until_complete(_delete_webhook_dev())
            except RuntimeError: asyncio.run(_delete_webhook_dev())
            application.run_polling(allowed_updates=ALLOWED_UPDATES_TYPES_STR_LIST, drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"CRITICAL ERROR during bot main execution loop: {e}", exc_info=True)
    finally:
        logger.info("--- Z1-Gray Bot application loop has concluded. ---")

if __name__ == "__main__":
    # from dotenv import load_dotenv
    # load_dotenv()
    main()