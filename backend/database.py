from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, ForeignKey
from datetime import datetime
from config import DATABASE_URL


engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_code = Column(String(30), unique=True, nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    description = Column(Text)
    specs = Column(JSON)
    current_stage = Column(String(50), default="FORMING", nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    # 1=Khẩn cấp  2=Bình thường  3=Thấp
    priority = Column(Integer, default=2)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class StageLog(Base):
    __tablename__ = "stage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)   # STARTED | COMPLETED | ISSUE
    note = Column(Text)
    operator = Column(String(100), default="System")
    timestamp = Column(DateTime, default=datetime.utcnow)


async def get_session() -> AsyncSession:  # type: ignore[override]
    async with async_session() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
