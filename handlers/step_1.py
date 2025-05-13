import asyncio
import logging
import datetime
import hashlib # For the placeholder generate_user_secure_id

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

# --- 假设的 helpers.py 位置和导入 ---
# 如果 utils 目录与 handlers 在同一级，且它们都是包（有__init__.py）
# from ..utils.helpers import generate_user_secure_id
# 如果 helpers.py 在项目根目录的 utils/ 下，并且项目根目录在 sys.path
# from utils.helpers import generate_user_secure_id

# --- 临时的 generate_user_secure_id 占位符 ---
# 请确保您有正确的 generate_user_secure_id 函数并能正确导入
# 如果您的 utils/helpers.py 如下：
# import hashlib
# def generate_user_secure_id(user_id_str: str) -> str:
#     return hashlib.md5(user_id_str.encode()).hexdigest()[:16]
# 那么上面的导入应该可以工作（根据您的项目结构调整）

# 为了代码能独立运行，这里放一个占位符实现
def generate_user_secure_id(user_id_str: str) -> str:
    """Generates a placeholder secure ID."""
    return hashlib.md5(user_id_str.encode()).hexdigest()[:16]
# --- End of placeholder ---


logger = logging.getLogger(__name__)

# --- Callback Data Constants ---
CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN = "s1_initiate_diagnostic_scan"
CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW = "s1_view_protocol_overview"
CALLBACK_S1_IGNORE_WARNING = "s1_ignore_warning"


async def start_step_1_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not update.message or not update.effective_chat:
        logger.warning("start_step_1_flow called without a message or effective_chat.")
        return
    if not user:
        logger.warning("Effective user is None in start_step_1_flow.")
        return

    user_id = user.id
    logger.info(f"User {user_id} ({user.username or 'N/A'}) started step_1_flow.")

    secure_id = generate_user_secure_id(str(user_id))
    context.user_data["secure_id"] = secure_id # 存储 secure_id 以便后续在其他回调中使用

    try:
        # 第1条消息
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html(
            "🔷 ACCESS NODE CONFIRMED\n"
            "→ PROTOCOL [Z1-GRAY_ΔPRIME] INITIALIZED"
        )
        await asyncio.sleep(1.5)

        # 第2条消息 + 时间戳
        timestamp_str = datetime.datetime.utcnow().strftime('%H:%M:%S.%f')[:-3] + ' UTC'
        message_text_2 = (
            f"→ TIMESTAMP: {timestamp_str}\n"
            f"🔹 SECURE IDENTIFIER GENERATED\n"
            f"→ USER_SECURE_ID: <code>{secure_id}</code>\n"
            f"→ AUTH_LAYER: 2B | SYNC_STATUS: PENDING"
        )
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html(message_text_2)
        await asyncio.sleep(2.7)

        # 第3条消息
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html(
            "⚠️ INITIAL NODE ANALYSIS: CRITICAL WARNING\n"
            "→ STABILITY RISK INDEX: 0.84 (ABOVE THRESHOLD)\n"
            "→ TRACE_SIGNAL: NON-STANDARD ALIGNMENT"
        )
        await asyncio.sleep(4.5)

        # 第4条消息
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html(
            "🔒 SYSTEM ALERT: Your access node has entered a volatility state.\n"
            "→ Interruption may trigger node quarantine protocol."
        )
        await asyncio.sleep(3.2)

        # 第5条消息
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html(
            "🧠 ACTION REQUIRED: Begin full TRACE_DIAGNOSTIC to determine node viability.\n"
            "→ Delayed response = elevated risk of deactivation"
        )
        await asyncio.sleep(2.8)

        # 行内按钮（视觉与心理冲击力强化版）
        keyboard = [
            [InlineKeyboardButton("🧪 RUN TRACE_DIAGNOSTIC NOW ⚡️", callback_data=CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN)],
            [InlineKeyboardButton("📄 VIEW SYSTEM PROTOCOL 📘", callback_data=CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW)],
            [InlineKeyboardButton("⛔️ IGNORE SYSTEM WARNING (NOT RECOMMENDED)", callback_data=CALLBACK_S1_IGNORE_WARNING)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_html("SELECT ACTION:", reply_markup=reply_markup)

        context.user_data["current_flow_step"] = "AWAITING_STEP_1_BUTTON"
        logger.info(f"User {user_id}: current_flow_step set to AWAITING_STEP_1_BUTTON. User data: {context.user_data}")

    except Exception as e:
        logger.error(f"Error in start_step_1_flow for user {user_id}: {e}", exc_info=True)
        if update.message:
            try:
                await update.message.reply_text(
                    "⚠️ System communication error during initialization. "
                    "Please try the /start sequence again shortly."
                )
            except Exception as e_reply:
                logger.error(f"Error sending error reply to user {user_id}: {e_reply}")


async def s1_view_protocol_overview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user

    if not query or not query.message:
        logger.warning("s1_view_protocol_overview_callback: Callback query or query.message is None.")
        if query: await query.answer()
        return
    
    user_id = user.id if user else "Unknown"
    logger.info(f"User {user_id} selected '{CALLBACK_S1_VIEW_PROTOCOL_OVERVIEW}'.")

    try:
        await query.answer()
        await query.message.reply_html(
            "📄 <b>System Protocol Overview</b> (Simplified Extract):\n\n"
            "<i>All access nodes are subject to periodic stability and alignment checks. "
            "Non-standard signal patterns or deviations from baseline parameters (ΔPrime) "
            "may indicate potential desynchronization risks. Active diagnostic measures are "
            "recommended to ensure continued node viability and prevent automated quarantine protocols.</i>\n\n"
            "⚠️ Your node has flagged for review. It is advised to <b>INITIATE TRACE_DIAGNOSTIC</b> promptly."
        )
    except Exception as e:
        logger.error(f"Error in s1_view_protocol_overview_callback for user {user_id}: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                text=query.message.text + "\n\n⚠️ Error loading protocol details. Please try again or proceed with diagnostics.",
                reply_markup=query.message.reply_markup
            )
        except Exception:
            try:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="⚠️ An error occurred while trying to display protocol information. Please try again."
                )
            except Exception as e_send:
                logger.error(f"Failed to send follow-up error to user {user_id}: {e_send}")


async def s1_initiate_diagnostic_scan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.message or not user:
        logger.warning("s1_initiate_diagnostic_scan_callback: Missing query, message, or user.")
        if query: await query.answer()
        return
    
    user_id = user.id
    logger.info(f"User {user_id} selected '{CALLBACK_S1_INITIATE_DIAGNOSTIC_SCAN}'.")
    await query.answer("Diagnostic scan initiating...")
    try:
        await query.edit_message_text(
            text="🔬 TRACE_DIAGNOSTIC INITIATED...\n"
                 "ANALYZING NODE STABILITY SIGNATURES.\n"
                 "PLEASE STAND BY."
        )
        context.user_data["current_flow_step"] = "STEP_1_DIAGNOSTIC_RUNNING"
        await asyncio.sleep(3)
        await query.message.reply_text("DIAGNOSTIC PHASE 1 COMPLETE. Node status report pending further system analysis.")

    except Exception as e:
        logger.error(f"Error in s1_initiate_diagnostic_scan_callback for user {user_id}: {e}", exc_info=True)
        if query.message:
            await query.message.reply_text("⚠️ Error initiating diagnostic. System integrity check recommended. Please try /start again.")


async def s1_ignore_warning_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user

    if not query or not query.message:
        logger.warning("s1_ignore_warning_callback: Callback query or query.message is None.")
        if query: await query.answer()
        return

    user_id = user.id if user else "Unknown"
    logger.info(f"User {user_id} selected '{CALLBACK_S1_IGNORE_WARNING}'. This is NOT recommended.")

    try:
        await query.answer("Processing decision...", show_alert=False)

        user_secure_id = context.user_data.get("secure_id", "UNKNOWN_NODE")

        await query.edit_message_text(
            text=f"{query.message.text}\n\n" # Keeps the "SELECT ACTION:" text from the original message
                 "🔴 <b>WARNING ACKNOWLEDGED & IGNORED</b> 🔴\n\n"
                 f"<i>Node <code>{user_secure_id}</code> is now flagged for potential instability.\n"
                 "Failure to address critical warnings may lead to automated\n"
                 "<b>NODE LOCKDOWN PROTOCOL</b> activation without further notice.</i>\n\n"
                 "Reconsideration is strongly advised. You may /start the process again to initiate diagnostics."
        )
        context.user_data["ignored_critical_warning_step1"] = True
        logger.warning(f"User {user_id} (Node: {user_secure_id}) has chosen to ignore the critical warning. Flag set.")

    except Exception as e:
        logger.error(f"Error in s1_ignore_warning_callback for user {user_id}: {e}", exc_info=True)
        if query.message:
            try:
                await query.message.reply_html(
                    "<b>ACTION RECORDED.</b>\n"
                    "<i>You have chosen to ignore the system warning. "
                    "This may have severe consequences for your node access. "
                    "Consider running diagnostics via /start.</i>"
                )
            except Exception as e_reply:
                 logger.error(f"Failed to send follow-up message after ignore error for user {user_id}: {e_reply}")