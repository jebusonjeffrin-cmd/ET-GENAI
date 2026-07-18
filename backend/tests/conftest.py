from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.dependencies import (
    get_document_repo,
    get_graph_store,
    get_keyword_store,
    get_llm_client,
    get_object_store,
    get_vector_store,
)
from app.llm.fake import FakeLLMClient
from app.main import create_app
from app.models.db_models import Base
from app.stores.document_repo import DocumentRepository
from app.stores.graph_store import FakeGraphStore
from app.stores.keyword_store import FakeKeywordStore
from app.stores.object_store import FakeObjectStore
from app.stores.vector_store import FakeVectorStore


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def fake_graph_store() -> FakeGraphStore:
    return FakeGraphStore()


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def fake_keyword_store() -> FakeKeywordStore:
    return FakeKeywordStore()


@pytest.fixture
def fake_object_store() -> FakeObjectStore:
    return FakeObjectStore()


@pytest_asyncio.fixture
async def test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(fake_llm, fake_graph_store, fake_vector_store, fake_keyword_store, fake_object_store, test_session):
    """A FastAPI test client with every external dependency swapped for a
    Fake* implementation via dependency_overrides — the app under test never
    touches Ollama, Neo4j, Postgres, or disk. See docs/TESTING.md."""
    app = create_app()
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    app.dependency_overrides[get_graph_store] = lambda: fake_graph_store
    app.dependency_overrides[get_vector_store] = lambda: fake_vector_store
    app.dependency_overrides[get_keyword_store] = lambda: fake_keyword_store
    app.dependency_overrides[get_object_store] = lambda: fake_object_store
    app.dependency_overrides[get_document_repo] = lambda: DocumentRepository(test_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
