from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.db_models import Base, DocumentRecord

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with SessionLocal() as session:
        yield session


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, record: DocumentRecord) -> DocumentRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get(self, document_id: str) -> DocumentRecord | None:
        return await self.session.get(DocumentRecord, document_id)

    async def list(self) -> list[DocumentRecord]:
        result = await self.session.execute(select(DocumentRecord).order_by(DocumentRecord.created_at.desc()))
        return list(result.scalars().all())

    async def update_status(self, document_id: str, status: str, error: str | None = None) -> None:
        record = await self.get(document_id)
        if record:
            record.status = status
            record.error = error
            await self.session.commit()
