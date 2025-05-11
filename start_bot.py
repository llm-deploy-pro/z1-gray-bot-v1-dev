import asyncio
import logging
import os
from pathlib import Path

from telegram.ext import Application, CommandHandler, CallbackQueryHandler
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
    """启动机器人"""
    # 从环境变量获取配置
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    webhook_url = os.getenv('WEBHOOK_URL')
    webhook_listen = os.getenv('WEBHOOK_LISTEN_IP', '0.0.0.0')
    webhook_port = int(os.getenv('WEBHOOK_PORT', '8443'))
    
    # 确保存储目录存在
    Path('./storage').mkdir(exist_ok=True)
    Path('./logs').mkdir(exist_ok=True)
    
    # 创建应用实例
    application = Application.builder().token(token).build()
    
    # 注册命令处理器
    application.add_handler(CommandHandler("start", step_1.start_step_1_flow))
    
    # TODO: 注册其他处理器
    
    # 设置Webhook
    mode = os.getenv('APP_ENV', 'development')
    if mode == 'production':
        application.run_webhook(
            listen=webhook_listen,
            port=webhook_port,
            url_path=webhook_url.split('/')[-1], 
            webhook_url=webhook_url
        )
    else:
        # 开发模式下使用轮询
        application.run_polling()

if __name__ == '__main__':
    main()
