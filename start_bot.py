# start_bot.py (Using a simple, fixed webhook path: "webhook")

import logging
import os
import asyncio
import hashlib # Still imported, but the hash itself is not directly used for WEBHOOK_PATH_SEGMENT

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from handlers import step_1

# --- CRITICAL ENVIRONMENT VARIABLE CHECK AT THE VERY TOP ---
# Using print for Render logs to ensure visibility before full logging setup
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

# --- MODIFICATION: Use a simple, fixed webhook path ---
WEBHOOK_PATH_SEGMENT = "webhook" # Using "webhook" as the fixed path segment
logger.info(f"Using fixed webhook path segment: '{WEBHOOK_PATH_SEGMENT}'")
# Ensure FULL_WEBHOOK_URL_FOR_TELEGRAM has a leading slash for the path segment
FULL_WEBHOOK_URL_FOR_TELEGRAM = f"{WEBHOOK_URL_BASE.rstrip('/')}/{WEBHOOK_PATH_SEGMENT.lstrip('/')}"
if not FULL_WEBHOOK_URL_FOR_TELEGRAM.split(WEBHOOK_URL_BASE.rstrip('/'))[-1].startswith('/'):
     # This check is a bit complex, simpler: ensure path segment itself does not start with / when constructing
     # For f"{base}/{segment}", if segment is "webhook", result is "base/webhook"
     # If segment is "/webhook", result is "base//webhook" (bad) or "base/webhook" (if rstrip works well)
     # Let's ensure WEBHOOK_PATH_SEGMENT itself doesn't have leading/trailing slashes for run_webhook's url_path
     WEBHOOK_PATH_SEGMENT = WEBHOOK_PATH_SEGMENT.strip('/') # Ensure no leading/trailing slashes for url_path
     FULL_WEBHOOK_URL_FOR_TELEGRAM = f"{WEBHOOK_URL_BASE.rstrip('/')}/{WEBHOOK_PATH_SEGMENT}"


# --- END OF MODIFICATION ---

PORT = int(os.environ.get("PORT", os.environ.get("WEBHOOK_PORT", 8443)))
ALLOWED_UPDATES_TYPES_STR_LIST = ["message", "callback_query"]


def main() -> None:
    logger.info(f"--- Starting Z1-Gray Bot (Fixed Path: /{WEBHOOK_PATH_SEGMENT}) ---")
    logger.info(f"Final APP_ENV: {APP_ENV}")
    logger.info(f"Final PORT: {PORT}")
    logger.info(f"Final WEBHOOK_URL_BASE for logic: {WEBHOOK_URL_BASE}")
    logger.info(f"Final FULL_WEBHOOK_URL_FOR_TELEGRAM: {FULL_WEBHOOK_URL_FOR_TELEGRAM}")
    logger.info(f"Final WEBHOOK_PATH_SEGMENT for run_webhook: '{WEBHOOK_PATH_SEGMENT}'")
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
            logger.info(f"Production mode: Calling application.run_webhook() with path '/{WEBHOOK_PATH_SEGMENT}'.")
            logger.info(
                f"  To manually verify (if issues persist):\n"
                f"  curl -F \"url={FULL_WEBHOOK_URL_FOR_TELEGRAM}\" -F \"allowed_updates={ALLOWED_UPDATES_TYPES_STR_LIST}\" https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
            )
            application.run_webhook(
                listen=os.environ.get("WEBHOOK_LISTEN_IP", "0.0.0.0"),
                port=PORT,
                url_path=WEBHOOK_PATH_SEGMENT, # Should be "webhook" (no leading/trailing slashes)
                webhook_url=FULL_WEBHOOK_URL_FOR_TELEGRAM, # Should be "https://.../webhook"
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