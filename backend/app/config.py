from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All external dependencies are configurable so the same code runs on this
    dev machine (no Ollama, no Docker) and on the laptop that actually has
    Ollama installed. See docs/PROJECT_PLAN.md §8 and docs/TESTING.md."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM backend: "fake" (default — no network, deterministic, used in
    # tests/dev/CI) or "ollama" (real inference against OLLAMA_HOST).
    llm_backend: str = "fake"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    ollama_embed_model: str = "nomic-embed-text"

    # Persistence — SQLite by default so nothing needs Docker to run tests or
    # `uvicorn app.main:app` locally. Point DATABASE_URL at Postgres for the
    # docker-compose / production path.
    database_url: str = "sqlite+aiosqlite:///./inspiron.db"

    # Graph store: "fake" (in-memory, default) or "neo4j" (real).
    graph_store_backend: str = "fake"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "inspiron_dev"

    # Vector store: in-memory only for now — PgVectorStore is a Phase 1
    # hardening item, not yet built. Tracked honestly, not hidden.
    vector_store_backend: str = "fake"

    # Object store: "fake" (in-memory, tests) or "local" (writes to disk).
    object_store_backend: str = "local"
    object_store_dir: str = "./data/objects"

    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
