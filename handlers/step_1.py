from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import asyncio

from utils.helpers import generate_user_secure_id

async def start_step_1_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Step 1: 系统初始化与身份锚定 - 启动流程
    
    处理/start命令，初始化协议并生成用户安全ID
    """
    # 获取用户ID
    user_id = update.effective_user.id
    
    # 生成安全ID
    secure_id = generate_user_secure_id(user_id)
    
    # 发送第1条消息
    await update.message.reply_html(
        "🔷 ACCESS NODE CONFIRMED\n"
        "→ PROTOCOL [Z1-GRAY_ΔPRIME] INITIALIZED"
    )
    
    # 等待1.2秒
    await asyncio.sleep(1.2)
    
    # 发送第2条消息
    await update.message.reply_html(
        f"🔹 SECURE IDENTIFIER GENERATED\n"
        f"→ USER_SECURE_ID: <code>{secure_id}</code>\n"
        f"→ AUTH_LAYER: 2B | SYNC_STATUS: PENDING"
    )
    
    # 等待2.3秒
    await asyncio.sleep(2.3)
    
    # 发送第3条消息
    await update.message.reply_html(
        "⚠️ INITIAL NODE ANALYSIS: CRITICAL WARNING\n"
        "→ STABILITY RISK INDEX: 0.84 (ABOVE THRESHOLD)\n"
        "→ TRACE_SIGNAL: NON-STANDARD ALIGNMENT"
    )
    
    # 等待3.8秒
    await asyncio.sleep(3.8)
    
    # 发送第4条消息
    await update.message.reply_html(
        "🔒 SYSTEM ALERT: Your access node has entered a volatility state.\n"
        "→ Interruption may trigger node quarantine protocol."
    )
    
    # 等待2.8秒
    await asyncio.sleep(2.8)
    
    # 发送第5条消息
    await update.message.reply_html(
        "🧠 ACTION REQUIRED: Begin full TRACE_DIAGNOSTIC to determine node viability.\n"
        "→ Delayed response = elevated risk of deactivation"
    )
    
    # 等待2.0秒
    await asyncio.sleep(2.0)
    
    # 创建行内键盘按钮
    keyboard = [
        [InlineKeyboardButton("INITIATE DIAGNOSTIC SCAN", callback_data="s1_initiate_diagnostic_scan")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 发送带按钮的消息
    await update.message.reply_html(
        "SELECT ACTION:", 
        reply_markup=reply_markup
    )
    
    # 在用户数据中存储当前流程步骤
    context.user_data["current_flow_step"] = "AWAITING_STEP_1_BUTTON"
