"""
Workflow engine — quản lý chuyển đổi trạng thái giữa 6 công đoạn xưởng gốm.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import Batch, StageLog

# ── Stage definitions ────────────────────────────────────────────────────────

STAGES = ["FORMING", "DRYING", "PAINTING", "GLAZING", "FIRING", "QC", "COMPLETED"]

STAGE_VI: Dict[str, str] = {
    "FORMING": "Tạo hình mộc",
    "DRYING": "Phơi sấy & Sửa mộc",
    "PAINTING": "Vẽ họa tiết",
    "GLAZING": "Tráng men",
    "FIRING": "Vào lò nung",
    "QC": "Kiểm định & Đóng gói",
    "COMPLETED": "Hoàn thành",
}

STAGE_EMOJI: Dict[str, str] = {
    "FORMING": "🏺",
    "DRYING": "☀️",
    "PAINTING": "🎨",
    "GLAZING": "✨",
    "FIRING": "🔥",
    "QC": "✅",
    "COMPLETED": "📦",
}


# ── Core operations ──────────────────────────────────────────────────────────

async def advance_batch(
    db: AsyncSession,
    batch_id: int,
    operator: str = "System",
    note: str = "",
    expected_stage: str = None,
) -> Optional[Dict[str, Any]]:
    """Chuyển mẻ gốm sang công đoạn tiếp theo."""
    res = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch: Optional[Batch] = res.scalar_one_or_none()
    if not batch:
        return None

    if expected_stage and batch.current_stage != expected_stage:
        raise ValueError(f"Batch đã chuyển khỏi công đoạn {expected_stage}")

    try:
        idx = STAGES.index(batch.current_stage)
    except ValueError:
        return None

    if idx >= len(STAGES) - 1:
        return None  # Already COMPLETED

    next_stage = STAGES[idx + 1]

    batch.current_stage = next_stage
    batch.updated_at = datetime.utcnow()
    if next_stage == "COMPLETED":
        batch.status = "COMPLETED"
    elif batch.status == "ISSUE":
        # Resolve issue when operator advances
        batch.status = "ACTIVE"

    log = StageLog(
        batch_id=batch_id,
        stage=next_stage,
        action="STARTED",
        note=note or f"Chuyển sang {STAGE_VI[next_stage]}",
        operator=operator,
    )
    db.add(log)
    await db.commit()

    return {
        "batch_id": batch_id,
        "order_code": batch.order_code,
        "product_name": batch.product_name,
        "quantity": batch.quantity,
        "stage": next_stage,
        "stage_name": STAGE_VI[next_stage],
        "stage_emoji": STAGE_EMOJI[next_stage],
        "operator": operator,
    }


async def flag_issue(
    db: AsyncSession,
    batch_id: int,
    issue: str,
    operator: str = "System",
) -> Optional[Dict[str, Any]]:
    """Đánh dấu sự cố cho mẻ gốm."""
    res = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch: Optional[Batch] = res.scalar_one_or_none()
    if not batch:
        return None

    batch.status = "ISSUE"
    batch.updated_at = datetime.utcnow()

    log = StageLog(
        batch_id=batch_id,
        stage=batch.current_stage,
        action="ISSUE",
        note=issue,
        operator=operator,
    )
    db.add(log)
    await db.commit()

    return {
        "batch_id": batch_id,
        "order_code": batch.order_code,
        "product_name": batch.product_name,
        "stage": batch.current_stage,
        "stage_name": STAGE_VI.get(batch.current_stage, batch.current_stage),
        "issue": issue,
    }

async def rework_batch(
    db: AsyncSession,
    batch_id: int,
    rework_qty: int,
    target_stage: str,
    operator: str = "System",
    note: str = "",
    expected_stage: str = None,
) -> Optional[Dict[str, Any]]:
    res = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch: Optional[Batch] = res.scalar_one_or_none()
    if not batch:
        return None

    if expected_stage and batch.current_stage != expected_stage:
        raise ValueError(f"Batch đã thay đổi công đoạn (hiện tại: {batch.current_stage}). Vui lòng tải lại trang.")

    if rework_qty <= 0 or rework_qty > batch.quantity:
        raise ValueError("Số lượng Rework không hợp lệ.")

    try:
        current_idx = STAGES.index(batch.current_stage)
        target_idx = STAGES.index(target_stage)
    except ValueError:
        raise ValueError("Công đoạn không hợp lệ.")

    if target_idx >= current_idx:
        raise ValueError("Chỉ được Rework về các công đoạn trước đó.")

    specs = batch.specs or {}
    rework_count = specs.get("rework_count", 0)
    
    if rework_count >= 2:
        raise ValueError("Mẻ con này đã vượt quá giới hạn Rework (tối đa 2 lần).")

    base_code = batch.order_code.split('-RW')[0]
    count_res = await db.execute(select(Batch.id).where(Batch.order_code.like(f"{base_code}%")))
    total_splits = len(count_res.fetchall())
    new_code = f"{base_code}-RW{total_splits}"

    reworked_batch = None
    
    if rework_qty == batch.quantity:
        batch.current_stage = target_stage
        batch.status = "ACTIVE"
        new_specs = specs.copy()
        new_specs["rework_count"] = rework_count + 1
        batch.specs = new_specs
        batch.updated_at = datetime.utcnow()
        reworked_batch = batch
        
        log = StageLog(batch_id=batch.id, stage=target_stage, action="REWORK", note=f"Rework toàn bộ. {note}", operator=operator)
        db.add(log)
    else:
        batch.quantity -= rework_qty
        batch.updated_at = datetime.utcnow()
        
        new_specs = specs.copy()
        new_specs["rework_count"] = rework_count + 1
        new_specs["parent_code"] = batch.order_code
        
        new_batch = Batch(
            order_code=new_code,
            product_name=batch.product_name,
            quantity=rework_qty,
            description=batch.description,
            specs=new_specs,
            current_stage=target_stage,
            status="ACTIVE",
            priority=batch.priority,
        )
        db.add(new_batch)
        await db.flush() 
        reworked_batch = new_batch
        
        log1 = StageLog(batch_id=batch.id, stage=batch.current_stage, action="SPLIT", note=f"Tách {rework_qty} cái lỗi sang {new_code}. {note}", operator=operator)
        db.add(log1)
        log2 = StageLog(batch_id=new_batch.id, stage=target_stage, action="REWORK", note=f"Tách từ {batch.order_code}. {note}", operator=operator)
        db.add(log2)

    await db.commit()
    return batch_to_dict(reworked_batch)


def batch_to_dict(batch: Batch) -> Dict[str, Any]:
    return {
        "id": batch.id,
        "order_code": batch.order_code,
        "product_name": batch.product_name,
        "quantity": batch.quantity,
        "description": batch.description,
        "specs": batch.specs,
        "current_stage": batch.current_stage,
        "stage_name": STAGE_VI.get(batch.current_stage, batch.current_stage),
        "stage_emoji": STAGE_EMOJI.get(batch.current_stage, ""),
        "status": batch.status,
        "priority": batch.priority,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "updated_at": batch.updated_at.isoformat() if batch.updated_at else None,
    }
