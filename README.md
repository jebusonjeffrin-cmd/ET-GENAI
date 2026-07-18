# Inspiron — Industrial Knowledge Intelligence Platform

Full plan: [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md). Testing strategy: [`docs/TESTING.md`](docs/TESTING.md). What's actually been built, phase by phase: [`docs/PROGRESS.md`](docs/PROGRESS.md). Moving this to the machine with Ollama: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

**Status:** all three core modules (Ingestion & Knowledge Graph, Expert Knowledge Copilot, Maintenance Intelligence & RCA Agent) have working, tested backends wired to real frontend UI — 49/49 backend tests, 15/15 frontend tests, all passing against `FakeLLMClient`. The one thing not yet done: running the three phase-gate scripts against **real** Ollama inference, because this dev machine has no GPU/Ollama. See `docs/DEPLOYMENT.md`.

## Why this runs on this machine with zero setup

Ollama lives on a different laptop. Every piece of code that talks to the model goes through an `LLMClient` interface (`backend/app/llm/`) — tests and local dev use `FakeLLMClient` (deterministic, no network), the real `OllamaLLMClient` only kicks in when `LLM_BACKEND=ollama`. Same pattern for the knowledge graph and vector/keyword index: `FakeGraphStore` / `FakeVectorStore` / `FakeKeywordStore` back everything by default, `Neo4jGraphStore` is the real adapter for when Neo4j is actually running. See `docs/TESTING.md` for the full reasoning.

## Quick start — backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate.bat for cmd, or source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt

pytest                          # 49 tests, ~1s — no Ollama, no Docker, no network
ruff check .
mypy app

uvicorn app.main:app --reload   # http://localhost:8000
```

## Quick start — frontend

```bash
cd frontend
npm install
npx vitest run                  # 15 tests
npx tsc --noEmit
npm run dev                     # http://localhost:5173
```

## Running against the real local model

**Step-by-step setup on the Ollama machine: see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).** Short version:

1. `ollama pull gemma3:4b && ollama pull nomic-embed-text` (once, on the Ollama machine).
2. Copy `backend/.env.example` to `backend/.env`; set `LLM_BACKEND=ollama` and `OLLAMA_HOST=http://localhost:11434`.
3. Run the functional-acceptance scripts against real inference:
   ```bash
   LLM_BACKEND=ollama python scripts/phase_gate/phase_1.py
   LLM_BACKEND=ollama python scripts/phase_gate/phase_2.py
   LLM_BACKEND=ollama python scripts/phase_gate/phase_3.py
   ```

## Full stack (Postgres / Neo4j / Redis)

```bash
docker compose up -d
```

## Deploying to the Ollama laptop

```
build here → commit → push to GitHub → clone/pull on the Ollama laptop → run there
```

`git push` always asks for confirmation (see `.claude/settings.json`) — nothing here auto-publishes. Full runbook: `docs/DEPLOYMENT.md`.
