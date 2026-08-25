"""
FastAPI main app — REST API + WebSocket hub cho GOM Pipeline.
"""
from __future__ import annotations

import asyncio
import json
import random
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

import telegram_bot
from database import Batch, StageLog, get_session, init_db
from schemas import AdvanceRequest, IssueRequest, OrderCreate, ReworkRequest
from workflow import STAGE_EMOJI, STAGE_VI, advance_batch, batch_to_dict, flag_issue
from worker import order_worker


# ── WebSocket hub ────────────────────────────────────────────────────────────

class Hub:
    def __init__(self) -> None:
        self._conns: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._conns.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._conns.discard(ws) if hasattr(self._conns, "discard") else None
        if ws in self._conns:
            self._conns.remove(ws)

    async def broadcast(self, payload: dict) -> None:
        msg = json.dumps(payload, ensure_ascii=False, default=str)
        dead: List[WebSocket] = []
        for ws in self._conns:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


hub = Hub()


# ── App lifecycle ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    order_worker.start(hub)
    await telegram_bot.start_bot()
    yield
    await order_worker.stop()
    await telegram_bot.stop_bot()


app = FastAPI(title="GOM Pipeline API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _new_order_code() -> str:
    ts = datetime.now().strftime("%m%d")
    rand = random.randint(10, 99)
    return f"GOM-{ts}-{rand}"


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.post("/api/orders", status_code=202)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_session),
):
    # Trả về 202 ngay lập tức, đưa vào queue
    batch = Batch(
        order_code=_new_order_code(),
        product_name="Đang chờ AI phân tích...",
        quantity=0,
        description=body.description,
        specs={},
        current_stage="FORMING",
        status="PENDING_PARSING",
        priority=2,
    )
    db.add(batch)
    await db.flush()  # Lấy ID
    
    await order_worker.push_job(
        batch_id=batch.id,
        description=body.description,
        operator=body.operator or "System"
    )
    await db.commit()
    
    return {"message": "Accepted", "batch_id": batch.id}


@app.get("/api/batches")
async def list_batches(db: AsyncSession = Depends(get_session)):
    res = await db.execute(select(Batch).order_by(desc(Batch.created_at)))
    return [batch_to_dict(b) for b in res.scalars().all()]


@app.get("/api/batches/{batch_id}")
async def get_batch(batch_id: int, db: AsyncSession = Depends(get_session)):
    res = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = res.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch not found")
    return batch_to_dict(batch)


@app.post("/api/batches/{batch_id}/advance")
async def advance(
    batch_id: int,
    body: AdvanceRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        result = await advance_batch(db, batch_id, body.operator or "System", body.note or "", body.expected_stage)
        if not result:
            raise HTTPException(400, "Cannot advance batch")
    except ValueError as e:
        raise HTTPException(400, str(e))

    res = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = res.scalar_one()

    payload = batch_to_dict(batch)
    await hub.broadcast({
        "type": "BATCH_ADVANCED",
        "batch": payload,
        "stage_name": result["stage_name"],
    })
    await telegram_bot.notify_stage_advance(batch, result["stage_name"], result["stage_emoji"])
    return result


@app.post("/api/batches/{batch_id}/issue")
async def report_issue(
    batch_id: int,
    body: IssueRequest,
    db: AsyncSession = Depends(get_session),
):
    result = await flag_issue(db, batch_id, body.issue, body.operator or "System")
    if result is None:
        raise HTTPException(404, "Batch not found")

    res = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = res.scalar_one()

    payload = batch_to_dict(batch)
    await hub.broadcast({
        "type": "BATCH_ISSUE",
        "batch": payload,
        "issue": body.issue,
    })
    await telegram_bot.notify_issue(batch, body.issue)
    return result


@app.post("/api/batches/{batch_id}/rework")
async def rework(
    batch_id: int,
    body: ReworkRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        from workflow import rework_batch
        result = await rework_batch(db, batch_id, body.rework_qty, body.target_stage, body.operator or "System", body.note or "", body.expected_stage)
        if not result:
            raise HTTPException(400, "Cannot rework batch")
    except ValueError as e:
        raise HTTPException(400, str(e))

    await hub.broadcast({"type": "BATCH_REWORKED"})
    
    # Notify Telegram
    res = await db.execute(select(Batch).where(Batch.id == result["id"]))
    reworked_batch = res.scalar_one()
    from telegram_bot import notify_rework
    asyncio.create_task(notify_rework(reworked_batch, body.target_stage, body.rework_qty, body.note or ""))

    return result


@app.get("/api/logs")
async def get_logs(
    order_code: str = None,
    stage: str = None,
    operator: str = None,
    db: AsyncSession = Depends(get_session)
):
    query = select(StageLog, Batch).join(Batch, StageLog.batch_id == Batch.id)
    
    if order_code:
        query = query.where(Batch.order_code.ilike(f"%{order_code}%"))
    if stage:
        query = query.where(StageLog.stage == stage)
    if operator:
        query = query.where(StageLog.operator.ilike(f"%{operator}%"))
        
    query = query.order_by(desc(StageLog.timestamp)).limit(100)
    res = await db.execute(query)
    
    return [
        {
            "id": log.id,
            "batch_id": log.batch_id,
            "order_code": batch.order_code,
            "product_name": batch.product_name,
            "stage": log.stage,
            "stage_name": STAGE_VI.get(log.stage, log.stage),
            "stage_emoji": STAGE_EMOJI.get(log.stage, ""),
            "action": log.action,
            "note": log.note,
            "operator": log.operator,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log, batch in res.all()
    ]


# ── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive ping
    except WebSocketDisconnect:
        hub.disconnect(websocket)


# ── Serve React build (production) ───────────────────────────────────────────

import os
_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse(os.path.join(_DIST, "index.html"))
