import logging
import os
import sys
from pathlib import Path
# import asyncio # 不再需要显式使用 asyncio.run
# from telegram import Bot # 不再需要 Bot 进行预清理
from telegram.error import Conflict as TelegramConflictError 

from telegram.ext import Application, CommandHandler
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO'))
)
logger = logging.getLogger(__name__)

# 导入处理模块
from handlers import step_1

# _pre_cleanup_webhook 函数已移除

def main():
    """主函数"""
    # 确保目录存在
    Path('./storage').mkdir(exist_ok=True)
    Path('./logs').mkdir(exist_ok=True)
    
    # 配置
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    webhook_url = os.getenv('WEBHOOK_URL') # 用于生产模式
    mode = os.getenv('APP_ENV', 'development')

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        sys.exit(1)

    # 不再有显式的 asyncio.run(_pre_cleanup_webhook(token)) 调用
            
    # 创建应用
    application = Application.builder().token(token).build()
    
    # 注册处理程序
    application.add_handler(CommandHandler("start", step_1.start_step_1_flow))
    
    # 初始化日志
    logger.info(f"Running in {mode} mode")
    
    # 根据模式启动
    if mode == 'production':
        # Webhook模式
        if not webhook_url:
            logger.error("WEBHOOK_URL environment variable not set for production mode!")
            sys.exit(1)
            
        webhook_port = int(os.getenv('WEBHOOK_PORT', '10000'))
        webhook_path = 'webhook' # 通常 webhook URL 的最后一部分，例如 /YOUR_BOT_TOKEN 或 /webhook
        webhook_listen = os.getenv('WEBHOOK_LISTEN_IP', '0.0.0.0')
        
        # 构建完整的 webhook URL，这是要设置给 Telegram 的 URL
        # 确保 webhook_url 在环境变量中是基础URL (https://yourdomain.onrender.com)
        full_webhook_to_set = f"{webhook_url.rstrip('/')}/{webhook_path}"

        logger.info(f"Starting webhook on {webhook_listen}:{webhook_port}, path: /{webhook_path}")
        logger.info(f"Webhook URL to be set with Telegram: {full_webhook_to_set}")
        
        application.run_webhook(
            listen=webhook_listen,
            port=webhook_port,
            url_path=webhook_path, # PTB 将在此路径上监听来自 Telegram 的更新
            webhook_url=full_webhook_to_set, # 完整的 URL，PTB 将用此 URL 调用 setWebhook
            drop_pending_updates=True
        )
    else:
        # 轮询模式
        logger.info("Starting polling mode")
        # run_polling 内部会进行初始化，包括尝试 delete_webhook
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except TelegramConflictError as e: 
        logger.error(f"Conflict error: {e}. This usually means another instance of the bot is running with the same token.")
        logger.error("Please ensure all other instances (local, remote, previous deployments) are stopped.")
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}", exc_info=True)
        sys.exit(1)
