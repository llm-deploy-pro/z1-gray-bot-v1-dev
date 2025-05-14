# start_bot.py (Final Optimized Version)

import logging
import os
import asyncio
import hashlib # For webhook path generation if you revert or use a different strategy

from telegram import Update # Used by ALLOWED_UPDATES_TYPES, good to have
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
# ContextTypes is not directly used here, but often imported for consistency if other parts of app use it.
# from telegram.ext import ContextTypes

# Import handlers module
from handlers import step_1

# --- CRITICAL ENVIRONMENT VARIABLE CHECK AT THE VERY TOP ---
# Using print for Render logs to ensure visibility before full logging setup,
# especially if basicConfig hasn't run or log levels are too high.
print(f"CRITICAL_ENV_PRINT_AT_TOP: RENDER_EXTERNAL_URL='{os.environ.get('RENDER_EXTERNAL_URL')}'")
print(f"CRITICAL_ENV_PRINT_AT_TOP: APP_ENV='{os.environ.get('APP_ENV')}'")
print(f"CRITICAL_ENV_PRINT_AT_TOP: PORT='{os.environ.get('PORT')}'")
print(f"CRITICAL_ENV_PRINT_AT_TOP: TELEGRAM_BOT_TOKEN_EXISTS='{'SET' if os.environ.get('TELEGRAM_BOT_TOKEN') else 'NOT_SET'}'")
# --- END OF CRITICAL ENV CHECK ---

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=os.environ.get("LOG_LEVEL", "INFO").upper() # Get log level from env, default to INFO
)
# Reduce verbosity of common libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO) # Keep INFO for PTB startup/webhook messages

logger = logging.getLogger(__name__)

# --- Environment Variable Configuration ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("FATAL: TELEGRAM_BOT_TOKEN environment variable not set!")
    exit(1)

APP_ENV = os.environ.get("APP_ENV", "development").lower()
WEBHOOK_URL_BASE_FROM_ENV = os.environ.get("RENDER_EXTERNAL_URL")

if APP_ENV == "production":
    if not WEBHOOK_URL_BASE_FROM_ENV:
        logger.critical("FATAL: RENDER_EXTERNAL_URL is MISSING for production on Render! Please set this in your Render service environment.")
        exit(1)
    if not WEBHOOK_URL_BASE_FROM_ENV.startswith("https://"):
        logger.critical(f"FATAL: RENDER_EXTERNAL_URL ('{WEBHOOK_URL_BASE_FROM_ENV}') must be an HTTPS URL for production webhook!")
        exit(1)
    WEBHOOK_URL_BASE = WEBHOOK_URL_BASE_FROM_ENV
else: # Development or other non-production
    WEBHOOK_URL_BASE = WEBHOOK_URL_BASE_FROM_ENV if WEBHOOK_URL_BASE_FROM_ENV else "http://localhost.placeholder.for.dev" # Does not need to be real for polling
    logger.info(f"Development mode. WEBHOOK_URL_BASE (may be placeholder): {WEBHOOK_URL_BASE}")

# Webhook Path Configuration
# Using a simple, fixed path as it proved to work on Render.
# If you want to revert to hashed path:
# WEBHOOK_PATH_SEGMENT = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:16]
WEBHOOK_PATH_SEGMENT = "webhook"
logger.info(f"Using webhook path segment: '{WEBHOOK_PATH_SEGMENT}'")

# Construct the full public URL for Telegram to send updates to
# Ensure no double slashes and path segment is correctly appended
_cleaned_base = WEBHOOK_URL_BASE.rstrip('/')
_cleaned_segment = WEBHOOK_PATH_SEGMENT.lstrip('/')
FULL_WEBHOOK_URL_FOR_TELEGRAM = f"{_cleaned_base}/{_cleaned_segment}" if _cleaned_segment else _cleaned_base


# Port Configuration
# Render provides PORT. For local dev, can use WEBHOOK_PORT from .env or a default.
DEFAULT_LOCAL_PORT = 8443
PORT = int(os.environ.get("PORT", os.environ.get("WEBHOOK_PORT", DEFAULT_LOCAL_PORT)))

# Allowed Updates Configuration (list of strings is generally safer for API calls)
ALLOWED_UPDATES_TYPES_STR_LIST = ["message", "callback_query"]


def main() -> None:
    """Configures and starts the Telegram Bot application."""
    bot_version = "1.0.0-optimized" # Example version
    logger.info(f"--- Starting Z1-Gray Bot ({bot_version}) ---")
    logger.info(f"Application Environment (APP_ENV): {APP_ENV}")
    logger.info(f"Effective Port for Listener: {PORT}")
    logger.info(f"Bot Token Suffix: ...{BOT_TOKEN[-4:]}") # Masked token for security

    # Create the Application instance
    # Consider adding persistence here if context.user_data needs to be saved across restarts
    # from telegram.ext import PicklePersistence
    # persistence = PicklePersistence(filepath="bot_data/z1_persistence.pickle") # Ensure directory exists
    # application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
    application = Application.builder().token(BOT_TOKEN).build()

    # --- Register Command and CallbackQuery Handlers ---
    application.add_handler(CommandHandler("start", step_1.start_step_1_flow))

    # Step 1 Button Callbacks
    application.add_handler(CallbackQueryHandler(step_1.s1_initiate_diagnostic_scan_callback, pattern=f"^{step_1.CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN}$"))
    application.add_handler(CallbackQueryHandler(step_1.s1_view_protocol_overview_callback, pattern=f"^{step_1.CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW}$"))
    application.add_handler(CallbackQueryHandler(step_1.s1_ignore_warning_callback, pattern=f"^{step_1.CALLBACK_S1_IGNORE_WARNING}$"))

    # Step 2 Entry Callbacks (all route to the same handler in step_1.py)
    application.add_handler(CallbackQueryHandler(
        step_1.step_2_entry_handler,
        pattern=r"^step2_entry_from_.*$" # Regex to match all Step 2 entry points
    ))
    logger.info("Registered command handlers and callback query handlers for Step 1 & Step 2 entries.")
    # --- End of Handler Registration ---

    try:
        if APP_ENV == "production":
            logger.info(f"Production mode: Initializing webhook application.")
            logger.info(f"  Listener will be on: {os.environ.get('WEBHOOK_LISTEN_IP', '0.0.0.0')}:{PORT}")
            logger.info(f"  Internal URL path for PTB: /{WEBHOOK_PATH_SEGMENT}")
            logger.info(f"  Public Webhook URL for Telegram API: {FULL_WEBHOOK_URL_FOR_TELEGRAM}")
            logger.info(
                f"  To manually verify/set webhook (if issues persist with auto-setup):\n"
                f"  curl -F \"url={FULL_WEBHOOK_URL_FOR_TELEGRAM}\" -F \"allowed_updates={ALLOWED_UPDATES_TYPES_STR_LIST}\" https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
            )

            # PTB's run_webhook handles calling bot.set_webhook internally
            application.run_webhook(
                listen=os.environ.get("WEBHOOK_LISTEN_IP", "0.0.0.0"), # Default to listen on all interfaces
                port=PORT,
                url_path=WEBHOOK_PATH_SEGMENT, # The path segment PTB's internal server listens on
                webhook_url=FULL_WEBHOOK_URL_FOR_TELEGRAM, # The full public URL passed to Telegram API
                allowed_updates=ALLOWED_UPDATES_TYPES_STR_LIST,
                drop_pending_updates=True # Recommended for production to clear queue on restart
            )
        else: # Development or other local environment
            logger.info(f"Development mode: Initializing polling application.")
            logger.info(f"  Allowed updates for polling: {ALLOWED_UPDATES_TYPES_STR_LIST}")

            # Asynchronously delete any existing webhook before starting polling in development
            async def _clear_webhook_for_dev(app: Application):
                logger.info("Attempting to clear any existing webhook for development polling...")
                try:
                    await app.bot.delete_webhook(drop_pending_updates=True)
                    logger.info("Webhook cleared successfully (or no webhook was set).")
                except Exception as e_del_wh:
                    logger.warning(f"Could not delete webhook in dev mode (this is often normal): {e_del_wh}")

            # Run the async function before starting polling
            # This is a common way to run a single async task from sync code
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running(): # e.g., in Jupyter or other already async env
                    asyncio.ensure_future(_clear_webhook_for_dev(application))
                else:
                    loop.run_until_complete(_clear_webhook_for_dev(application))
            except RuntimeError: # Fallback if get_event_loop() fails (e.g. no current loop set on thread)
                 asyncio.run(_clear_webhook_for_dev(application))


            application.run_polling(
                allowed_updates=ALLOWED_UPDATES_TYPES_STR_LIST,
                drop_pending_updates=True # Changed to True for cleaner dev starts, was False
            )
    except Exception as e:
        logger.critical(f"CRITICAL ERROR during bot main execution loop: {e}", exc_info=True)
        logger.critical(
            "--- Bot CRASHED or stopped unexpectedly. "
            "Manual intervention likely required. Please check full logs. ---"
        )
    finally:
        # This block executes whether the try block completes successfully or an exception occurs
        logger.info("--- Z1-Gray Bot application run loop has concluded. ---")

if __name__ == "__main__":
    # If using a .env file for local development, uncomment the following:
    # from dotenv import load_dotenv
    # load_dotenv() # Loads variables from .env into os.environ

    # For Windows asyncio event loop policy if needed (usually for Python < 3.8)
    # if os.name == 'nt' and sys.version_info < (3, 8):
    #    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()