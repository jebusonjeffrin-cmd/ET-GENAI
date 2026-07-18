from __future__ import annotations

import asyncio

from app.config import get_settings
from app.ingestion.celery_app import celery_app
from app.ingestion.pipeline import IngestionPipeline
from app.llm.fake import FakeLLMClient
from app.stores.document_repo import DocumentRepository, SessionLocal
from app.stores.graph_store import FakeGraphStore
from app.stores.object_store import LocalDiskObjectStore
from app.stores.vector_store import FakeVectorStore


@celery_app.task(name="ingestion.process_document")
def process_document_task(document_id: str, filename: str, data: bytes) -> None:
    """Async ingestion path matching the architecture in docs/PROJECT_PLAN.md §3
    (requires a running Redis broker + worker). The synchronous path in
    app/api/routes/documents.py is what today's demo actually exercises;
    this task exists so the async architecture is real code, not just a
    diagram, and can be switched on once a broker is running.

    KNOWN LIMITATION (documented, not hidden): this task currently uses
    process-local FakeGraphStore/FakeVectorStore, so writes from one worker
    process are not visible to the API process. Swap for Neo4jGraphStore /
    a real vector store before relying on this path — tracked as a Phase 1
    hardening item.
    """
    asyncio.run(_run(document_id, filename, data))


async def _run(document_id: str, filename: str, data: bytes) -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        document_repo = DocumentRepository(session)
        llm = _real_llm() if settings.llm_backend == "ollama" else FakeLLMClient()
        pipeline = IngestionPipeline(
            llm=llm,
            graph_store=FakeGraphStore(),
            vector_store=FakeVectorStore(),
            object_store=LocalDiskObjectStore(settings.object_store_dir),
            document_repo=document_repo,
        )
        await pipeline.run(document_id, filename, data)


def _real_llm():
    from app.llm.ollama_client import OllamaLLMClient

    return OllamaLLMClient()
