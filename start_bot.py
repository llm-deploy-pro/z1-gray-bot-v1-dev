import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse # 用于解析 webhook URL

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler, # 需要导入
    PicklePersistence # 可选，用于持久化 user_data
)
from telegram.error import Conflict as TelegramConflictError
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# --- 配置日志 ---
# Render 通常会收集 stdout/stderr，所以基础配置通常足够
# 如果要写入文件，确保在 Render 上有持久化存储或接受日志可能丢失
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_file_path_str = os.getenv('LOG_FILE_PATH')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, log_level_str, logging.INFO),
    handlers=[logging.StreamHandler(sys.stdout)] # 强制输出到 stdout
)
# 如果同时需要文件日志：
# if log_file_path_str:
#     file_handler = logging.FileHandler(log_file_path_str)
#     file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
#     logging.getLogger().addHandler(file_handler)

logger = logging.getLogger(__name__)

# --- 导入处理模块 ---
# 假设你的 handlers 文件夹与 start_bot.py 在同一级或 Python路径可达
from handlers import step_1 # 用于 start_step_1_flow
# 你需要为 step_1 中的按钮回调创建一个处理函数，并在这里导入
# 例如，如果回调函数也在 step_1.py 中:
# from handlers.step_1 import s1_initiate_diagnostic_scan_callback

def main() -> None:
    """主函数，启动机器人"""
    # --- 确保目录存在 ---
    Path('./storage').mkdir(parents=True, exist_ok=True)
    Path('./logs').mkdir(parents=True, exist_ok=True) # 如果使用文件日志

    # --- 配置 ---
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    app_env = os.getenv('APP_ENV', 'development').lower()

    admin_ids_str = os.getenv('ADMIN_USER_IDS', '')
    admin_ids = [int(admin_id.strip()) for admin_id in admin_ids_str.split(',') if admin_id.strip()]
    logger.info(f"Admin IDs: {admin_ids}")


    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        sys.exit(1)

    # --- 持久化 (可选) ---
    # 如果你使用了 context.user_data 并且希望在重启后保留它们
    persistence = PicklePersistence(filepath="./storage/bot_persistence_data")

    # --- 创建应用 ---
    application = (
        Application.builder()
        .token(token)
        .persistence(persistence) # 添加持久化
        .build()
    )

    # --- 注册处理程序 ---
    application.add_handler(CommandHandler("start", step_1.start_step_1_flow))

    # 为 step_1.py 中创建的按钮注册 CallbackQueryHandler
    # 确保 s1_initiate_diagnostic_scan_callback 在 step_1.py 中定义并导入
    application.add_handler(
        CallbackQueryHandler(step_1.s1_initiate_diagnostic_scan_callback, pattern="^s1_initiate_diagnostic_scan$")
    )
    # ... 其他命令和回调处理器 ...


    logger.info(f"Bot starting in {app_env} mode.")

    # --- 根据模式启动 ---
    if app_env == 'production':
        # --- Webhook 模式 (用于 Render) ---
        webhook_full_url = os.getenv('WEBHOOK_URL') # e.g., https://your-app.onrender.com/webhook/path
        if not webhook_full_url:
            logger.error("WEBHOOK_URL environment variable not set for production mode!")
            sys.exit(1)

        # 从完整的 WEBHOOK_URL 中提取路径部分
        parsed_url = urlparse(webhook_full_url)
        webhook_path_segment = parsed_url.path  # e.g., "/webhook/path"

        if not webhook_path_segment or webhook_path_segment == '/':
            logger.error(f"Could not determine a valid webhook path from WEBHOOK_URL: {webhook_full_url}")
            sys.exit(1)

        # Render 会设置 PORT 环境变量，你的应用必须监听这个端口
        # .env 中的 WEBHOOK_PORT 可以作为备用，但 Render 的 PORT 优先
        port_str = os.getenv('PORT', os.getenv('WEBHOOK_PORT'))
        if not port_str:
            logger.error("PORT or WEBHOOK_PORT environment variable not set for production mode!")
            sys.exit(1)
        port = int(port_str)

        listen_ip = os.getenv('WEBHOOK_LISTEN_IP', '0.0.0.0') # Render 通常需要 0.0.0.0

        logger.info(f"Webhook Mode: Setting webhook to {webhook_full_url}")
        logger.info(f"Webhook Mode: Listening on {listen_ip}:{port} at path {webhook_path_segment}")

        try:
            application.run_webhook(
                listen=listen_ip,
                port=port,
                url_path=webhook_path_segment, # PTB 将在此路径上监听
                webhook_url=webhook_full_url,   # PTB 将用此 URL 调用 setWebhook
                drop_pending_updates=True,
                # secret_token="YOUR_SECRET_TOKEN_IF_ANY" # 可选，用于增强安全性
            )
        except Exception as e:
            logger.error(f"Failed to run webhook: {e}", exc_info=True)
            sys.exit(1)

    else:
        # --- 轮询模式 (用于本地开发) ---
        logger.info("Development Mode: Starting polling...")
        # run_polling 会尝试删除任何现有的 webhook
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES # 明确指定接收所有类型的更新
        )

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt).")
        sys.exit(0)
    except TelegramConflictError:
        logger.error(
            "Telegram Conflict Error: Another instance of the bot is running with the same token, "
            "or a webhook is set while trying to poll. "
            "Please ensure only one instance is active and the webhook is cleared if polling."
            "You can manually clear it by visiting: https://api.telegram.org/bot<YOUR_TOKEN>/deleteWebhook"
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred in main execution: {e}", exc_info=True)
        sys.exit(1)