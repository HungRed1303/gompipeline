import asyncio
from typing import TypedDict
from datetime import datetime

from sqlalchemy import select
from database import async_session, Batch, StageLog
from ai_agent import parse_order
import telegram_bot
from workflow import batch_to_dict

class OrderJob(TypedDict):
    batch_id: int
    description: str
    operator: str

class OrderQueueWorker:
    def __init__(self, concurrency: int = 2):
        self.queue: asyncio.Queue[OrderJob] = asyncio.Queue()
        self.concurrency = concurrency
        self.workers: list[asyncio.Task] = []
        self.hub = None

    def start(self, hub):
        self.hub = hub
        for i in range(self.concurrency):
            task = asyncio.create_task(self._worker_loop(i))
            self.workers.append(task)
            
    async def stop(self):
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        
    async def push_job(self, batch_id: int, description: str, operator: str):
        await self.queue.put({
            "batch_id": batch_id,
            "description": description,
            "operator": operator
        })
        
    async def _worker_loop(self, worker_id: int):
        while True:
            try:
                job = await self.queue.get()
                await self._process_job(job)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                import traceback
                print(f"[Worker-{worker_id}] Error processing job:")
                traceback.print_exc()
                
    async def _process_job(self, job: OrderJob):
        batch_id = job['batch_id']
        desc = job['description']
        op = job['operator']
        
        print(f"[Worker] Parsing batch_id={batch_id} via LLM...")
        
        # 1. LLM parsing (this is blocking, we should ideally run it in a threadpool)
        # However, for simplicity in asyncio, since genai is synchronous mostly,
        # we run it in executor to avoid blocking the event loop.
        loop = asyncio.get_event_loop()
        specs = await loop.run_in_executor(None, parse_order, desc)
        
        # 2. Update DB
        async with async_session() as db:
            res = await db.execute(select(Batch).where(Batch.id == batch_id))
            batch = res.scalar_one_or_none()
            if not batch:
                print(f"[Worker] Batch {batch_id} not found!")
                return
                
            batch.specs = specs
            batch.product_name = specs.get("product_name", desc[:60])
            batch.quantity = specs.get("quantity", 1)
            batch.priority = specs.get("priority", 2)
            batch.status = "ACTIVE"
            batch.current_stage = "FORMING"
            batch.updated_at = datetime.utcnow()
            
            log = StageLog(
                batch_id=batch.id,
                stage="FORMING",
                action="STARTED",
                note="Đơn hàng mới — bắt đầu Tạo hình mộc",
                operator=op,
            )
            db.add(log)
            await db.commit()
            await db.refresh(batch)
            
            payload = batch_to_dict(batch)
            
        # 3. Broadcast and Notify
        if self.hub:
            await self.hub.broadcast({"type": "BATCH_CREATED", "batch": payload})
        await telegram_bot.notify_new_batch(batch)
        print(f"[Worker] Completed batch_id={batch_id}")

order_worker = OrderQueueWorker(concurrency=2)
