import logging
import os
import sys
from pathlib import Path

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

def main():
    """主函数"""
    # 确保目录存在
    Path('./storage').mkdir(exist_ok=True)
    Path('./logs').mkdir(exist_ok=True)
    
    # 配置
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    webhook_url = os.getenv('WEBHOOK_URL')
    mode = os.getenv('APP_ENV', 'development')
    
    # 创建应用
    application = Application.builder().token(token).build()
    
    # 注册处理程序
    application.add_handler(CommandHandler("start", step_1.start_step_1_flow))
    
    # 初始化
    logger.info(f"Running in {mode} mode")
    
    # 根据模式启动
    if mode == 'production':
        # Webhook模式
        webhook_port = int(os.getenv('WEBHOOK_PORT', '10000'))
        webhook_path = 'webhook'
        webhook_listen = os.getenv('WEBHOOK_LISTEN_IP', '0.0.0.0')
        
        logger.info(f"Starting webhook on {webhook_listen}:{webhook_port}")
        logger.info(f"Webhook URL: {webhook_url}")
        
        # 在webhook模式下启动
        application.run_webhook(
            listen=webhook_listen,
            port=webhook_port,
            url_path=webhook_path,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        # 轮询模式
        logger.info("Starting polling mode")
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
