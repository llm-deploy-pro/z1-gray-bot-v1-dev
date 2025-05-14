import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from utils.helpers import TimedMessage, send_delayed_sequence, send_system_error_reply

STEP_2_SCAN_COMPLETE_AWAITING_S3 = "step_2_scan_complete_awaiting_s3"
CALLBACK_S3_VIEW_DIAGNOSIS = "s3_view_diagnosis"

logger = logging.getLogger(__name__)

async def execute_step_2_scan_sequence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query or not update.callback_query.message or not update.effective_user:
        logger.error("[Step ②] execute_step_2_scan_sequence called with invalid Update or User context.")
        user_id_for_error = update.effective_user.id if update.effective_user else "Unknown"
        if user_id_for_error == "Unknown" and context.user_data and "user_id" in context.user_data:
            user_id_for_error = context.user_data["user_id"]
        await send_system_error_reply(update.callback_query if update.callback_query else None, context, user_id_for_error, "Internal error processing Step ② sequence (E401).")
        return

    chat_id = update.callback_query.message.chat_id
    user_id = update.effective_user.id
    context.user_data["user_id"] = user_id
    user_secure_id = context.user_data.get("secure_id", "NODE_ID_MISSING")

    if context.user_data.get("current_flow_step") == STEP_2_SCAN_COMPLETE_AWAITING_S3:
        logger.warning(f"[Step ②] User {user_id} re-triggered completed scan (current_flow_step is {STEP_2_SCAN_COMPLETE_AWAITING_S3}). Ignoring repeat execution.")
        try:
            await update.callback_query.answer("Scan already completed. Proceed to Step ③ if available.")
        except Exception as e_answer:
            logger.warning(f"Failed to answer callback query for re-trigger: {e_answer}")
        return

    logger.info(f"[Step ②] Executing deep scan message sequence for user_id: {user_id} ({user_secure_id})")

    # --- 使用您最初定义的“剧本原文”（英文术语 + 指定中文解释） ---
    step_2_scan_messages = [
        TimedMessage(
            text="📡 Initiating Signal Resonance Scan...\n→ 追踪节点信号启动中…", # 严格按照您最初给的剧本
            delay_before=2.5, typing=True,
            system_log=f"[RESONANCE_LOCKED: USER_PATTERN_MATCH → GAMMA-7-SIG :: {user_secure_id}]" # system_log 保留之前的优化
        ),
        TimedMessage(
            text="⚠️ SIGNAL_VARIANCE = Δ0.83\n→ 当前节点出现信号漂移偏差 Δ0.83", # 严格按照您最初给的剧本
            delay_before=3.0, typing=True,
            system_log=f"[SIGNAL_PROFILE_DEVIATION_LOGGED: Δ0.83 → USER_ADAPTIVE_REALIGNMENT_QUEUED :: {user_secure_id}]"
        ),
        TimedMessage(
            text="🧠 NODE STABILITY STATUS = DEGRADED\n→ 节点稳定性等级：已降级", # 严格按照您最初给的剧本
            delay_before=2.0, typing=True,
            system_log=f"[STABILITY_TRACE_TRIGGERED: CORE_PATTERN_DISSONANCE_DETECTED → ESCALATED TO TRACKER-L2 :: {user_secure_id}]"
        ),
        TimedMessage(
            text="🔒 SYSTEM_LOCK ACTIVE\n→ 外部输入已锁定，系统自适应排查中…", # 严格按照您最初给的剧本
            delay_before=2.5, typing=True,
            system_log=f"[SECURE_SCAN_MODE_ENABLED → NODE_ISOLATION_FOR_USER: {user_secure_id}]"
        ),
        TimedMessage(
            text="📉 TRACE SIGNAL INTEGRITY = 67.3% (BELOW SAFE THRESHOLD)\n→ 信号完整性不足，当前状态已低于安全临界", # 严格按照您最初给的剧本
            delay_before=3.0, typing=True,
            system_log=f"[THRESHOLD_BREACH → ATTRACTOR_LINK: DEGRADED — NODE_ID: {user_secure_id}]"
        ),
        TimedMessage(
            text="🧬 NODE ANOMALY LEVEL = UNSUPERVISED\n→ 当前异常未被用户主动触发\n→ 建议进行深度诊断以避免节点剔除。", # 严格按照您最初给的剧本
            delay_before=3.5, typing=True,
            system_log=f"[ANOMALY_TYPE: OMEGA-4 — USER_NODE_FLAGGED_FOR_PRIORITY_OBSERVATION :: {user_secure_id}]"
        ),
    ]
    # --- END OF MESSAGES ---

    try:
        await send_delayed_sequence(context.bot, chat_id, step_2_scan_messages, initial_delay=0.8)
        logger.info(f"[Step ②] Core message sequence completed for user {user_id} ({user_secure_id})")

        context.user_data["current_flow_step"] = STEP_2_SCAN_COMPLETE_AWAITING_S3
        logger.info(f"[Step ②] User {user_id} ({user_secure_id}) state marked as {STEP_2_SCAN_COMPLETE_AWAITING_S3}")

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(2.0)

        keyboard_to_s3 = InlineKeyboardMarkup([[
            InlineKeyboardButton("▶️ 获取权威诊断及唯一修复协议 (步骤 ③)", callback_data=CALLBACK_S3_VIEW_DIAGNOSIS)
        ]])

        # 这个引导至步骤三的中文消息保持不变，因为它在剧本中是作为Step 2结束后的引导，且包含ACCESS_KEY术语
        transition_message_text = (
            "📊 <b>扫描分析已完成。</b>\n\n"
            "您的节点状态需<b><u>立即处理</u></b>。\n"
            "系统已锁定针对此状态的<b>唯一修复路径</b>。\n\n"
            "进入步骤 ③ 查看诊断报告并激活修复协议。\n"
            "<b>警告：</b>延迟操作可能导致当前访问密钥 (ACCESS_KEY) 失效及节点资格审查。"
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=transition_message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_to_s3
        )
        logger.info(f"[Step ②] Guided user {user_id} ({user_secure_id}) to Step ③ with callback {CALLBACK_S3_VIEW_DIAGNOSIS}")

    except Exception as e:
        logger.error(f"[Step ②] Error during execute_step_2_scan_sequence for user {user_id} ({user_secure_id}): {e}", exc_info=True)
        await send_system_error_reply(update.callback_query, context, user_id, "An error occurred during the node scan process (E402).")