import asyncio
import logging # 添加 logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
# from telegram.constants import ParseMode # ParseMode 已被弃用，直接在 reply_html 中使用 HTML

# 假设你的 helpers.py 在 utils 文件夹下
from utils.helpers import generate_user_secure_id

logger = logging.getLogger(__name__) # 为此模块创建 logger

async def start_step_1_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Step 1: 系统初始化与身份锚定 - 启动流程
    处理/start命令，初始化协议并生成用户安全ID
    """
    user = update.effective_user
    if not user:
        logger.warning("Effective user is None in start_step_1_flow.")
        return

    user_id = user.id
    logger.info(f"User {user_id} ({user.username or 'N/A'}) started step 1 flow.")

    # 生成安全ID
    secure_id = generate_user_secure_id(str(user_id)) # 确保 user_id 是字符串

    try:
        # 发送第1条消息
        await update.message.reply_html(
            "🔷 ACCESS NODE CONFIRMED\n"
            "→ PROTOCOL [Z1-GRAY_ΔPRIME] INITIALIZED"
        )

        await asyncio.sleep(1.2)

        # 发送第2条消息
        await update.message.reply_html(
            f"🔹 SECURE IDENTIFIER GENERATED\n"
            f"→ USER_SECURE_ID: <code>{secure_id}</code>\n"
            f"→ AUTH_LAYER: 2B | SYNC_STATUS: PENDING"
        )

        await asyncio.sleep(2.3)

        # 发送第3条消息
        await update.message.reply_html(
            "⚠️ INITIAL NODE ANALYSIS: CRITICAL WARNING\n"
            "→ STABILITY RISK INDEX: 0.84 (ABOVE THRESHOLD)\n"
            "→ TRACE_SIGNAL: NON-STANDARD ALIGNMENT"
        )

        await asyncio.sleep(3.8)

        # 发送第4条消息
        await update.message.reply_html(
            "🔒 SYSTEM ALERT: Your access node has entered a volatility state.\n"
            "→ Interruption may trigger node quarantine protocol."
        )

        await asyncio.sleep(2.8)

        # 发送第5条消息
        await update.message.reply_html(
            "🧠 ACTION REQUIRED: Begin full TRACE_DIAGNOSTIC to determine node viability.\n"
            "→ Delayed response = elevated risk of deactivation"
        )

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

        # 在用户数据中存储当前流程步骤 (需要启用并配置持久化)
        context.user_data["current_flow_step"] = "AWAITING_STEP_1_BUTTON"
        logger.info(f"User {user_id}: current_flow_step set to AWAITING_STEP_1_BUTTON. User data: {context.user_data}")

    except Exception as e:
        logger.error(f"Error in start_step_1_flow for user {user_id}: {e}", exc_info=True)
        if update.message:
            await update.message.reply_text("An error occurred while processing your request. Please try again later.")


async def s1_initiate_diagnostic_scan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 "INITIATE DIAGNOSTIC SCAN" 按钮的回调
    """
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        logger.warning("Callback query or effective user is None in s1_initiate_diagnostic_scan_callback.")
        if query: await query.answer() # 尝试应答以移除加载状态
        return

    user_id = user.id
    logger.info(f"User {user_id} pressed 'INITIATE DIAGNOSTIC SCAN' button.")

    # 必须先应答回调查询
    await query.answer("Diagnostic scan initiating...")

    try:
        # 编辑原始消息，例如移除按钮并显示新状态
        await query.edit_message_text(
            text="🔬 TRACE_DIAGNOSTIC INITIATED...\n"
                 "ANALYZING NODE STABILITY SIGNATURES.\n"
                 "PLEASE STAND BY."
        )

        # 在用户数据中更新状态
        context.user_data["current_flow_step"] = "STEP_1_DIAGNOSTIC_RUNNING"
        logger.info(f"User {user_id}: current_flow_step set to STEP_1_DIAGNOSTIC_RUNNING. User data: {context.user_data}")

        # 这里可以开始下一步的逻辑，例如发送新的消息或等待某些异步操作
        # await asyncio.sleep(5) # 模拟诊断操作
        # await query.message.reply_text("Diagnostic complete. Proceed to step 2: /step2_command")

    except Exception as e:
        logger.error(f"Error in s1_initiate_diagnostic_scan_callback for user {user_id}: {e}", exc_info=True)
        # 尝试通知用户错误
        if query.message:
            await query.message.reply_text("An error occurred while initiating the scan. Please try again.")
        else: # 如果原始消息无法访问，尝试通过 context.bot.send_message
            try:
                await context.bot.send_message(chat_id=user_id, text="An error occurred. Please try the command again.")
            except Exception as send_err:
                logger.error(f"Failed to send error message to user {user_id}: {send_err}")