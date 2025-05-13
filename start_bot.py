import logging
import os
import asyncio
import hashlib # For ❗问题 3: Webhook path hashing

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes, # Though not directly used here, good for consistency if other modules expect it
)

# 导入 handlers 模块中的函数和常量
# 确保 handlers 是一个可导入的包（即 handlers 文件夹下有 __init__.py）
from handlers import step_1 # Assuming step_2_entry_handler and S2 callbacks are in step_1.py for now
# If step_2_entry_handler moves to a step_2.py, you'd import that too:
# from handlers import step_2

# 配置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO) # Keep INFO for PTB startup messages

logger = logging.getLogger(__name__)

# --- 从环境变量获取配置 ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("FATAL: TELEGRAM_BOT_TOKEN environment variable not set!")
    exit(1)

WEBHOOK_URL_BASE = os.environ.get("RENDER_EXTERNAL_URL")
# For production, RENDER_EXTERNAL_URL is critical for webhook
APP_ENV = os.environ.get("APP_ENV", "development").lower()

if APP_ENV == "production" and not WEBHOOK_URL_BASE:
    logger.critical("FATAL: RENDER_EXTERNAL_URL environment variable not set! This is required for webhook in production on Render.")
    exit(1)

# ❗问题 3：Webhook 路径可被轻易猜测（使用 TOKEN） - 可选强化方式
# Option 1: Keep using BOT_TOKEN (simpler, common)
# WEBHOOK_PATH = BOT_TOKEN
# Option 2: Use a hash (more secure if path needs to be obscure)
WEBHOOK_PATH = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:16] # Using a shorter part of the hash
logger.info(f"Using hashed webhook path segment for security: {WEBHOOK_PATH}")

# Ensure WEBHOOK_URL_BASE is set for constructing FULL_WEBHOOK_URL, even if it's a placeholder for local dev
if not WEBHOOK_URL_BASE:
    WEBHOOK_URL_BASE = "https://your.dev.server.com" # Placeholder for local if not set
    if APP_ENV == "production": # Double check, should have exited above
        logger.error("CRITICAL: WEBHOOK_URL_BASE somehow became unset for production. Exiting.")
        exit(1)
    logger.warning(f"RENDER_EXTERNAL_URL not set, using placeholder for FULL_WEBHOOK_URL: {WEBHOOK_URL_BASE}")


FULL_WEBHOOK_URL = f"{WEBHOOK_URL_BASE.rstrip('/')}/{WEBHOOK_PATH.lstrip('/')}"
PORT = int(os.environ.get("PORT", 8443)) # Render default is 10000, 8443 is a common alt

# ❗问题 5：未配置 allowed_updates 白名单精简（可选优化）
ALLOWED_UPDATES_TYPES = [Update.MESSAGE, Update.CALLBACK_QUERY] # Or more specific: ["message", "callback_query"] using strings

async def post_init(application: Application) -> None:
    """Post-initialization hook for the Application."""
    if APP_ENV == "production":
        logger.info(f"Setting webhook for production: {FULL_WEBHOOK_URL}")
        await application.bot.set_webhook(
            url=FULL_WEBHOOK_URL,
            allowed_updates=ALLOWED_UPDATES_TYPES,
            drop_pending_updates=True # Good for production to clear queue on restart
        )
        # ❗问题 4：Webhook 路径未明确打印 TELEGRAM 设置建议命令
        logger.info(
            f"Webhook set. To manually verify or test (e.g., if auto-set fails), you can use:\n"
            f"curl -F \"url={FULL_WEBHOOK_URL}\" -F \"allowed_updates={ALLOWED_UPDATES_TYPES}\" https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        )
    else: # Development - ensure webhook is cleared
        logger.info("Development mode: Ensuring any existing webhook is cleared before starting polling.")
        # ❗问题 2：Webhook 删除逻辑在 polling 分支注释未启用 (启用)
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook cleared successfully for polling mode.")


def main() -> None:
    """配置并启动 Telegram Bot."""
    logger.info(f"--- Starting Z1-Gray Bot (vX.Y.Z) ---") # Consider adding a version
    logger.info(f"Application Environment (APP_ENV): {APP_ENV}")
    logger.info(f"Bot Token: ...{BOT_TOKEN[-4:]}") # Masked token

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init) # Use post_init for async setup like set_webhook
        .build()
    )

    # --- 注册 Command 和 CallbackQuery Handlers ---
    application.add_handler(CommandHandler("start", step_1.start_step_1_flow))

    # Step 1 Callbacks
    application.add_handler(CallbackQueryHandler(step_1.s1_initiate_diagnostic_scan_callback, pattern=f"^{step_1.CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN}$"))
    application.add_handler(CallbackQueryHandler(step_1.s1_view_protocol_overview_callback, pattern=f"^{step_1.CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW}$"))
    application.add_handler(CallbackQueryHandler(step_1.s1_ignore_warning_callback, pattern=f"^{step_1.CALLBACK_S1_IGNORE_WARNING}$"))

    # ❗问题 1：未注册 Step 2 的入口回调（CallbackQueryHandler）
    # Assuming step_2_entry_handler and S2 callback constants are defined in handlers.step_1 module
    # If they were in handlers.step_2, you'd use step_2.step_2_entry_handler etc.
    application.add_handler(CallbackQueryHandler(
        step_1.step_2_entry_handler, # This is the unified handler
        pattern=r"^step2_entry_from_.*$" # Regex to match all step2 entry points
    ))
    logger.info("Registered Step 1 and Step 2 entry callback handlers.")
    # --- End of handler registration ---

    try:
        if APP_ENV == "production":
            logger.info(f"Production mode: Starting webhook listener on 0.0.0.0:{PORT} for path /{WEBHOOK_PATH}")
            application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=WEBHOOK_PATH, # Handled by PTB, matches path in FULL_WEBHOOK_URL
                # webhook_url is set by post_init now, so not needed here explicitly
                # allowed_updates are also set by post_init
            )
        else: # development or other local environment
            logger.info(f"Development mode: Starting polling with allowed_updates: {ALLOWED_UPDATES_TYPES}")
            application.run_polling(
                allowed_updates=ALLOWED_UPDATES_TYPES,
                drop_pending_updates=False # For dev, you might want to see pending updates initially
            )
    except Exception as e:
        logger.critical(f"CRITICAL ERROR during bot execution: {e}", exc_info=True)
        # ✅ 建议添加：异常终止后的重启提示 (修改日志级别和内容)
        logger.critical("--- Bot CRASHED or stopped unexpectedly. Manual intervention likely required. Check full logs. ---")
    finally:
        # This will run if run_polling/run_webhook finishes gracefully OR due to an unhandled exception in their loop
        logger.info("--- Z1-Gray Bot application loop has ended. ---")


if __name__ == "__main__":
    # For Windows, ensure the correct asyncio event loop policy if issues arise
    # if os.name == 'nt' and sys.version_info >= (3, 8):
    #    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()