import logging
import os
import asyncio # 虽然主逻辑在webhook，但handlers可能用

from telegram import Update # Update 在handlers里用
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes, # ContextTypes 在handlers里用
    # MessageHandler, # 如果有其他消息处理
    # filters, # 如果有其他消息处理
)

# 导入 handlers 模块中的函数和常量
# 确保 handlers 是一个可导入的包（即 handlers 文件夹下有 __init__.py）
from handlers import step_1
# 如果上面的导入方式有问题，并且 handlers 与 start_bot.py 在同一项目根目录，
# 确保 Python 的模块搜索路径正确。

# 配置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
# PTB 的日志比较啰嗦，可以调整特定模块的日志级别
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO) # 或者 WARNING

logger = logging.getLogger(__name__)

# --- 从环境变量获取配置 ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("FATAL: TELEGRAM_BOT_TOKEN environment variable not set!")
    exit(1) # 明确退出

# Render 会自动设置 RENDER_EXTERNAL_URL
WEBHOOK_URL_BASE = os.environ.get("RENDER_EXTERNAL_URL")
if not WEBHOOK_URL_BASE:
    logger.critical("FATAL: RENDER_EXTERNAL_URL environment variable not set! This is required for webhook on Render.")
    exit(1) # 明确退出

WEBHOOK_PATH = BOT_TOKEN # 使用 Bot Token 作为路径是一种常见且安全的做法
FULL_WEBHOOK_URL = f"{WEBHOOK_URL_BASE.rstrip('/')}/{WEBHOOK_PATH.lstrip('/')}"

# Render 会通过 PORT 环境变量指定端口，通常是 10000
# 本地开发时可以设置一个备用端口，例如 8443 或 5000
PORT = int(os.environ.get("PORT", 8443))

# 判断运行环境，例如 'production' (在Render上) 或 'development' (本地)
APP_ENV = os.environ.get("APP_ENV", "development").lower()


def main() -> None:
    """配置并启动 Telegram Bot."""
    logger.info(f"--- Starting Z1-Gray Bot ---")
    logger.info(f"Application Environment (APP_ENV): {APP_ENV}")
    logger.info(f"Bot Token: {'*' * (len(BOT_TOKEN) - 4) + BOT_TOKEN[-4:]}") # Masked token

    # 创建 Application 实例
    # 可以考虑在这里配置持久化，如果 user_data 需要跨重启保留
    # from telegram.ext import PicklePersistence
    # persistence = PicklePersistence(filepath="bot_persistence")
    # application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
    application = Application.builder().token(BOT_TOKEN).build()

    # --- 注册 Command 和 CallbackQuery Handlers ---
    # /start 命令的处理
    application.add_handler(CommandHandler("start", step_1.start_step_1_flow))

    # Step 1 中的按钮回调
    application.add_handler(CallbackQueryHandler(
        step_1.s1_initiate_diagnostic_scan_callback,
        pattern=f"^{step_1.CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN}$"
    ))
    application.add_handler(CallbackQueryHandler(
        step_1.s1_view_protocol_overview_callback,
        pattern=f"^{step_1.CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW}$"
    ))
    application.add_handler(CallbackQueryHandler(
        step_1.s1_ignore_warning_callback,
        pattern=f"^{step_1.CALLBACK_S1_IGNORE_WARNING}$"
    ))
    # --- End of handler registration ---

    # 根据运行环境选择启动方式
    if APP_ENV == "production":
        logger.info(f"CRITICAL CHECK: Production mode detected. Starting webhook.")
        logger.info(f"Webhook will listen on 0.0.0.0:{PORT}")
        logger.info(f"Webhook path: /{WEBHOOK_PATH}")
        logger.info(f"Webhook URL to be set with Telegram: {FULL_WEBHOOK_URL}")

        # 在生产环境中，通常建议在启动时设置 webhook，并清理旧的
        # PTB 的 run_webhook 会自动处理 set_webhook
        application.run_webhook(
            listen="0.0.0.0",  # 必须是 0.0.0.0 才能被 Render 外部访问
            port=PORT,
            url_path=WEBHOOK_PATH,
            webhook_url=FULL_WEBHOOK_URL,
            drop_pending_updates=True # 生产环境通常建议清除旧更新
        )
    else: # development or other local environment
        logger.info(f"CRITICAL CHECK: Development mode detected. Starting polling.")
        logger.info("Clearing any existing webhook before starting polling...")
        # asyncio.run(application.bot.delete_webhook(drop_pending_updates=True)) # 确保清除
        application.run_polling(
            allowed_updates=Update.ALL_TYPES, # 根据需要调整
            drop_pending_updates=True
        )

    logger.info("--- Z1-Gray Bot has shut down or encountered an unhandled error ---")

if __name__ == "__main__":
    # 确保在 Windows 上 asyncio 事件循环策略正确 (如果本地开发在 Windows)
    # if os.name == 'nt':
    #    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()