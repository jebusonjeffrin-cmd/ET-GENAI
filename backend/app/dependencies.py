from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.llm.base import LLMClient
from app.llm.fake import FakeLLMClient
from app.stores.document_repo import DocumentRepository, get_session
from app.stores.graph_store import FakeGraphStore, GraphStore
from app.stores.object_store import FakeObjectStore, LocalDiskObjectStore, ObjectStore
from app.stores.vector_store import FakeVectorStore, VectorStore

# In-memory stores are process-local singletons so writes made by one request
# (e.g. an upload) are visible to a later request (e.g. a graph search) within
# the same running server — that's what makes the demo coherent. Tests bypass
# these entirely via FastAPI's dependency_overrides (see tests/conftest.py),
# so each test gets a fresh, isolated store.
_shared_graph_store = FakeGraphStore()
_shared_vector_store = FakeVectorStore()
_shared_object_store: ObjectStore | None = None
_shared_llm: LLMClient | None = None


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    global _shared_llm
    if _shared_llm is not None:
        return _shared_llm
    if settings.llm_backend == "ollama":
        from app.llm.ollama_client import OllamaLLMClient

        _shared_llm = OllamaLLMClient()
    else:
        _shared_llm = FakeLLMClient()
    return _shared_llm


def get_graph_store(settings: Settings = Depends(get_settings)) -> GraphStore:
    if settings.graph_store_backend == "neo4j":
        from app.stores.graph_store import Neo4jGraphStore

        return Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    return _shared_graph_store


def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStore:
    # NOTE: always the in-memory FakeVectorStore for now — a real PgVectorStore
    # is a Phase 1 hardening item, not yet built (see docs/PROJECT_PLAN.md §5).
    return _shared_vector_store


def get_object_store(settings: Settings = Depends(get_settings)) -> ObjectStore:
    global _shared_object_store
    if _shared_object_store is None:
        _shared_object_store = (
            FakeObjectStore() if settings.object_store_backend == "fake" else LocalDiskObjectStore(settings.object_store_dir)
        )
    return _shared_object_store


async def get_document_repo(session: AsyncSession = Depends(get_session)) -> DocumentRepository:
    return DocumentRepository(session)
