"""
Telegram Bot — gửi thông báo và xử lý inline-button callback từ thợ / quản lý.
Chạy song song với FastAPI thông qua lifespan hook.
"""
from __future__ import annotations
import sys

# Fix Windows terminal không hiển thị được emoji / tiếng Việt
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from typing import TYPE_CHECKING, Optional

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from workflow import STAGE_VI

if TYPE_CHECKING:
    from database import Batch

# Application instance (khởi tạo khi start_bot được gọi)
_app = None
# Lưu trữ {batch_id: message_id} để xoá các button cũ khi chuyển sang công đoạn mới
_pending_messages: dict[int, int] = {}


async def start_bot() -> None:
    global _app
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️  TELEGRAM_BOT_TOKEN chưa cấu hình — bỏ qua Telegram bot")
        return

    from telegram.ext import Application, CallbackQueryHandler

    _app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    _app.add_handler(CallbackQueryHandler(_handle_callback))

    await _app.initialize()
    await _app.start()
    await _app.updater.start_polling(drop_pending_updates=True)
    print("✅ Telegram bot đã khởi động")


async def stop_bot() -> None:
    if _app is None:
        return
    await _app.updater.stop()
    await _app.stop()
    await _app.shutdown()


# ── Notification helpers ─────────────────────────────────────────────────────

async def _send(text: str, reply_markup=None):
    if _app is None or not TELEGRAM_CHAT_ID:
        return None
    try:
        return await _app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    except Exception as exc:
        print(f"[Telegram] send error: {exc}")
        return None


async def notify_new_batch(batch: "Batch") -> None:
    specs = batch.specs or {}
    lines = [
        f"🆕 <b>Đơn hàng mới — #{batch.order_code}</b>",
        f"📦 {batch.product_name}",
        f"🔢 Số lượng: <b>{batch.quantity} cái</b>",
        f"🏺 Bắt đầu: <b>Tạo hình mộc</b>",
    ]
    if specs.get("firing_temp_c"):
        lines.append(f"🌡️ Nhiệt độ nung: <b>{specs['firing_temp_c']}°C</b>")
    if specs.get("deadline_days"):
        lines.append(f"📅 Deadline: <b>{specs['deadline_days']} ngày</b>")
    if specs.get("clay_kg_estimate"):
        lines.append(f"🪨 Đất sét ước tính: <b>{specs['clay_kg_estimate']} kg</b>")
    await _send("\n".join(lines))


async def notify_stage_advance(batch: "Batch", stage_name: str, stage_emoji: str) -> None:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Xóa button của message cũ nếu có
    if batch.id in _pending_messages:
        old_msg_id = _pending_messages.pop(batch.id)
        if _app and TELEGRAM_CHAT_ID:
            try:
                await _app.bot.edit_message_reply_markup(
                    chat_id=TELEGRAM_CHAT_ID,
                    message_id=old_msg_id,
                    reply_markup=None
                )
            except Exception as e:
                print(f"[Telegram] Failed to clear old markup: {e}")

    text = (
        f"{stage_emoji} <b>Mẻ gốm #{batch.order_code}</b>\n"
        f"✅ Đã vào công đoạn: <b>{stage_name}</b>\n"
        f"📦 {batch.product_name} × {batch.quantity}"
    )

    if batch.current_stage == "COMPLETED":
        text += "\n\n🎉 <b>Đơn hàng đã hoàn thành!</b>"
        await _send(text)
        return

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Xác nhận hoàn thành", callback_data=f"confirm_{batch.id}_{batch.current_stage}"),
        InlineKeyboardButton("⚠️ Báo sự cố", callback_data=f"issue_{batch.id}"),
    ]])
    msg = await _send(text, reply_markup=kb)
    if msg:
        _pending_messages[batch.id] = msg.message_id


async def notify_issue(batch: "Batch", issue: str) -> None:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    text = (
        f"🚨 <b>CẢNH BÁO SỰ CỐ — #{batch.order_code}</b>\n"
        f"📦 {batch.product_name} × {batch.quantity}\n"
        f"📍 Công đoạn: <b>{batch.current_stage}</b>\n"
        f"🔴 Vấn đề: {issue}\n\n"
        f"⚡ Quản lý xưởng vui lòng xử lý ngay!"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔧 Đã xử lý — Tiếp tục", callback_data=f"confirm_{batch.id}_{batch.current_stage}"),
    ]])
    await _send(text, reply_markup=kb)


async def notify_rework(batch: "Batch", target_stage: str, rework_qty: int, note: str) -> None:
    target_vi = STAGE_VI.get(target_stage, target_stage)
    text = (
        f"♻️ <b>TÁCH MẺ / REWORK — #{batch.order_code}</b>\n"
        f"📦 {batch.product_name} × {rework_qty}\n"
        f"📍 Quay lại công đoạn: <b>{target_vi}</b>\n"
        f"🔴 Lý do: {note}"
    )
    await _send(text)


# ── Callback handler ─────────────────────────────────────────────────────────

async def _handle_callback(update, context) -> None:
    query = update.callback_query
    await query.answer()

    data: str = query.data
    user_name: str = query.from_user.first_name or "Không rõ"

    if data.startswith("confirm_"):
        parts = data.split("_")
        batch_id = int(parts[1])
        expected_stage = parts[2] if len(parts) > 2 else None
        
        _pending_messages.pop(batch_id, None)
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"http://localhost:8000/api/batches/{batch_id}/advance",
                    json={"operator": f"TG:{user_name}", "note": "Xác nhận qua Telegram", "expected_stage": expected_stage},
                )
            if resp.status_code == 200:
                result = resp.json()
                await query.edit_message_text(
                    f"✅ <b>{user_name}</b> đã xác nhận!\n"
                    f"▶ Chuyển sang: <b>{result.get('stage_name', '')}</b>",
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(
                    "❌ Từ chối: Mẻ gốm này đã được chuyển công đoạn trên hệ thống trước đó!"
                )
        except Exception as exc:
            await query.edit_message_text(f"❌ Lỗi kết nối server: {exc}")

    elif data.startswith("issue_"):
        await query.edit_message_text(
            "⚠️ Đã ghi nhận. Vui lòng mô tả sự cố chi tiết hơn qua Web Dashboard.",
            parse_mode="HTML",
        )
