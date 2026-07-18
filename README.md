# Inspiron — Industrial Knowledge Intelligence Platform

Full plan: [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md). Testing strategy: [`docs/TESTING.md`](docs/TESTING.md).

**Status:** Phase 0 (UI shell) + Phase 1 (ingestion & knowledge graph backend) built and passing tests. Copilot and Maintenance/RCA screens exist as complete, polished UI on fixture data — their real backends are Phase 2 and Phase 3.

## Why this runs on this machine with zero setup

Ollama lives on a different laptop. Every piece of code that talks to the model goes through an `LLMClient` interface (`backend/app/llm/`) — tests and local dev use `FakeLLMClient` (deterministic, no network), the real `OllamaLLMClient` only kicks in when `LLM_BACKEND=ollama`. Same pattern for the knowledge graph and vector index: `FakeGraphStore` / `FakeVectorStore` back everything by default, `Neo4jGraphStore` is the real adapter for when Neo4j is actually running. See `docs/TESTING.md` for the full reasoning.

## Quick start — backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate.bat for cmd, or source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt

pytest                          # 17 tests, ~0.3s — no Ollama, no Docker, no network
ruff check .
mypy app

uvicorn app.main:app --reload   # http://localhost:8000
```

## Quick start — frontend

```bash
cd frontend
npm install
npx vitest run                  # 9 tests
npx tsc --noEmit
npm run dev                     # http://localhost:5173
```

## Running against the real local model (on the Ollama laptop)

1. On that laptop: `ollama pull gemma3:4b && ollama pull nomic-embed-text` (once).
2. Copy `backend/.env.example` to `backend/.env`; set `LLM_BACKEND=ollama` and `OLLAMA_HOST` (LAN IP if testing remotely from this machine, or `http://localhost:11434` once this code actually runs on that laptop).
3. `pytest -m phase_gate` runs the functional-acceptance checks against real inference (`docs/TESTING.md`).

## Full stack (Postgres / Neo4j / Redis)

```bash
docker compose up -d
```

## Deploying to the Ollama laptop

```
build here → commit → push to GitHub → clone/pull on the Ollama laptop → run there
```

`git push` always asks for confirmation (see `.claude/settings.json`) — nothing here auto-publishes.
