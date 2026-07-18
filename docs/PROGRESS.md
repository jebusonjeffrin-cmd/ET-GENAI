# Inspiron — Progress Log

Running record of what's actually been built, phase by phase. Append a new entry per phase — don't rewrite history. See `docs/PROJECT_PLAN.md` for the plan and `docs/TESTING.md` for the testing strategy this log verifies against.

---

## Phase 0 + Phase 1 — done (2026-07-18)

### What was built

**Backend** (`backend/`)
- FastAPI + Celery skeleton.
- Core architectural pattern: every external dependency — LLM, knowledge graph, vector index, object storage — sits behind an interface (`LLMClient`, `GraphStore`, `VectorStore`, `ObjectStore`) with a `Fake*` implementation for tests/dev and a real adapter for deployment. This is what makes the codebase buildable and testable on this machine even though Ollama lives on a separate laptop.
- Phase 1 ingestion pipeline, real end to end: upload → parse (`pypdf`/plain text, degrades gracefully on unsupported formats) → structured extraction → knowledge graph write → embedding. Wired to live `/documents` (upload, list, get) and `/graph` (`/equipment/{tag}`, `/stats`) endpoints.
- `OllamaLLMClient` defaults to **`gemma3:4b`** (4B params), overridable via `OLLAMA_MODEL` env var to match whatever's actually pulled on the deployment laptop.
- Celery async task path exists (`app/ingestion/tasks.py`) matching the architecture diagram, but isn't the exercised path yet — the sync path in the API route is what the demo runs today. Documented as a known limitation, not hidden.

**Frontend** (`frontend/`)
- Full Vite + React + TypeScript + Tailwind shell across all six Phase 0 screens: Home, Document Library, Knowledge Graph Explorer, Copilot, Maintenance & RCA, Admin. Role switcher (Field Technician / Maintenance Engineer / RCA Lead / Admin).
- **Document Library, Knowledge Graph Explorer, and Admin are wired to the real Phase 1 backend** — not mocked.
- **Copilot and Maintenance & RCA are complete, polished UI on fixture data** — their backends are Phase 2 and Phase 3, not built yet. Per plan, nothing says "coming soon."

**Testing & CI**
- `.github/workflows/ci.yml` runs the full backend + frontend test suite (mocked LLM, service containers for Postgres/Neo4j/Redis) on every push.
- `docs/TESTING.md` documents the strategy: the `LLMClient`/`FakeLLMClient` pattern, the test pyramid, and why CI can never run the phase-gate functional-acceptance checks (no GPU/Ollama in GitHub Actions — those stay manual, on whichever machine reaches real Ollama).

### Verification actually run (not just claimed)

| Check | Result |
|---|---|
| Backend tests (`pytest`) | **17/17 passed** |
| Backend lint (`ruff check .`) | **clean** |
| Backend types (`mypy app`) | **clean** (fixed 5 real type errors: unsound `BaseModel`-vs-`T` generics in `LLMClient`, unguarded `Optional` access in the Neo4j stats query and the document-upload route, `UploadFile.filename` nullability) |
| Backend coverage | **71%** — gap is exactly the real Neo4j/Ollama adapters, which only run once deployed against actual services (expected, documented) |
| Frontend tests (`vitest run`) | **9/9 passed** |
| Frontend types (`tsc --noEmit`) | **clean** |
| Frontend production build (`vite build`) | **succeeds** |

### Key decisions made this phase

- **Scope locked to 3 modules** (Ingestion+KG, Copilot, Maintenance/RCA) — Compliance and Lessons Learned cut, documented as roadmap-only. See `PROJECT_PLAN.md` §1.
- **Fully local, self-hosted LLM inference** — no Claude/OpenAI/any hosted API anywhere in the pipeline. See `PROJECT_PLAN.md` §5.
- **Dev machine ≠ Ollama machine.** Everything LLM-touching goes through `LLMClient` so the dev machine never needs Ollama installed to build or test. Workflow: build here → commit → push to GitHub (asks for confirmation every time, never auto-approved) → clone/pull on the Ollama laptop → run there.
- **Persistence pragmatism:** SQLite by default (no Docker needed for `pytest`/`uvicorn`), Postgres wired in `docker-compose.yml` for the full-stack path. `PgVectorStore` is a known, tracked gap — vector search is in-memory (`FakeVectorStore`) even in the "production" compose file today.
- **Git state:** repo initialized locally, one commit, **not pushed**. No GitHub remote configured yet.

### Known gaps / honest limitations carried forward

- `PgVectorStore` not built — vector search is in-memory only, fine at hackathon corpus size, won't scale past that.
- Celery async ingestion path is written but not the exercised path (API route runs sync); the worker path also currently uses process-local Fake graph/vector stores, so it won't share state with the API process until wired to Neo4j/a real vector store.
- No OCR/vision pass yet — unsupported binary formats (xlsx, images, most P&IDs) degrade to a placeholder string rather than being parsed. Flagged in `parsing.py` and `PROJECT_PLAN.md` §5, not silently swallowed.
- Frontend tests cover the shell, Copilot's mock flow, and Document Library's fetch states — Knowledge Graph Explorer and Admin don't have dedicated frontend tests yet.

### Next phase

**Phase 2 — Expert Knowledge Copilot.** Per `PROJECT_PLAN.md` §7: hybrid retrieval (vector + keyword + one-hop graph expansion), local-LLM streaming synthesis with citation markers mapped back to source spans, WebSocket chat transport, wire the already-built Copilot UI to it. Testing gate: retrieval ranking + citation-mapping unit tests, chat endpoint integration tests, ≥15-question benchmark functional-acceptance run against the Phase 1 corpus, regression check that Phase 1 still passes.

---

## Phase 2 — Expert Knowledge Copilot — done (2026-07-18)

### What was built

**Backend** (`backend/`)
- `FakeKeywordStore`/`KeywordStore` (`app/stores/keyword_store.py`) — in-memory token-overlap (Jaccard) keyword search, same Fake-first pattern as every other store. Real search-engine backend (OpenSearch/BM25) is a tracked gap, not built.
- `HybridRetriever` (`app/retrieval/hybrid.py`) — combines vector similarity, keyword overlap, and one-hop graph expansion (regex-extracted equipment tags → `graph_store.get_equipment_360()` → linked documents pulled in as supplementary context even if they had no vector/keyword hit). Dedupes chunks found by both vector and keyword search, tagging them `vector+keyword`.
- `CopilotService` (`app/copilot/service.py`) — builds a numbered-source prompt, calls `LLMClient.chat_stream`, and maps `[n]` citation markers in the model's output back to the actual retrieved chunks (document ID, chunk ID, source text). Works against any `LLMClient`, so the exact same code path runs against `FakeLLMClient` in tests and `OllamaLLMClient` in production.
- `/copilot/ask` (REST, synchronous, response includes citations) and `/copilot/stream` (WebSocket, token-by-token) — both wired via `app/api/routes/copilot.py`.
- Ingestion pipeline now indexes every chunk into the keyword store as well as the vector store (`IngestionPipeline._index_chunks`, renamed from `_write_embeddings`).
- Phase 2 functional-acceptance scripts added: `backend/scripts/phase_gate/phase_2.py` (5-question starter benchmark, extend to ≥15 before treating as a real sign-off) and, retroactively, `phase_1.py` (Phase 1 didn't have one — closing that gap now rather than leaving `docs/TESTING.md`'s reference to it inaccurate).

**Frontend** (`frontend/`)
- Copilot page rewritten to call `POST /copilot/ask` for real — no longer fixture-only. Shows the backend's actual answer, real citations (`[n] document <id>`), a loading state, and a graceful error message if the backend is unreachable.

### Verification actually run

| Check | Result |
|---|---|
| Backend tests (`pytest`) | **34/34 passed** (17 Phase 1 + 17 new Phase 2 — zero regressions) |
| Backend lint (`ruff check .`) | **clean** (includes the new `scripts/phase_gate/` files) |
| Backend types (`mypy app`) | **clean** |
| Backend coverage | **76%** — gap is the WebSocket streaming handler (see limitation below) plus the same real-adapter gap as Phase 1 |
| Frontend tests (`vitest run`) | **11/11 passed** (was 9 — added 2 Copilot cases: error path, empty-answer fallback) |
| Frontend types (`tsc --noEmit`) | **clean** |
| Frontend production build (`vite build`) | **succeeds** |

### Key decisions made this phase

- **Keyword search is a heuristic (Jaccard token overlap), not BM25** — deliberate hackathon-speed tradeoff, same honesty pattern as `FakeVectorStore` in Phase 1. Good enough to prove the hybrid-retrieval architecture; a real search engine is a swap-in later, not a rewrite (same interface).
- **Graph expansion only fires on regex-matched equipment tags** (`[A-Z]{1,3}-\d{2,4}`, matching the ontology's tag format) — no LLM call needed to detect them, keeps retrieval fast and fully offline-testable.
- **Citations are extracted by parsing `[n]` markers from the model's own output**, not a separate structured-output call — cheaper, and it's exactly how a human reads a cited answer, so what's tested is what's actually displayed.
- **REST endpoint is the tested path; WebSocket is real but unverified by automation.** Testing FastAPI WebSocket routes needs the synchronous `TestClient`, which risks event-loop conflicts with this project's async-fixture pattern (`test_session` created under `pytest-asyncio`'s loop). Rather than force a fragile test, the gap is documented in `app/api/routes/copilot.py` itself and here. The frontend doesn't consume `/copilot/stream` yet either — it uses `/copilot/ask`.
- **Git:** remote added (`https://github.com/jebusonjeffrin-cmd/ET-GENAI`), Phase 0+1 commit pushed. `git push` still asks for confirmation every time — this was an explicit, one-time user instruction to wire the remote, not a standing auto-push permission.

### Known gaps / honest limitations carried forward

- Everything listed under Phase 0+1 above still applies (`PgVectorStore`, OCR/vision, Celery worker state-sharing).
- `/copilot/stream` WebSocket endpoint has no automated test (see above) — exercise it manually before relying on it for the live demo.
- Frontend has no dedicated test for Knowledge Graph Explorer or Admin yet (carried forward from Phase 1).
- Phase 2's real functional-acceptance benchmark (≥15 questions, human-reviewed citation accuracy) has **not** been run — `scripts/phase_gate/phase_2.py` exists and is ready, but needs `LLM_BACKEND=ollama` against a real Ollama instance, which this dev machine doesn't have. Run it on the Ollama laptop before calling Phase 2 truly gated, not just unit-tested.

### Next phase

**Phase 3 — Maintenance Intelligence & RCA Agent.** Per `PROJECT_PLAN.md` §7: custom tools (`search_equipment_history`, `get_work_orders`, `get_similar_incidents`) and a tool-use loop against the local model's native function-calling API that gathers evidence before drafting an RCA chain. Wire the already-built Equipment Health Dashboard, Work Order Explorer, RCA Workspace, and Maintenance Schedule view to it. Testing gate: unit tests per tool in isolation, integration test of the full tool-use loop, ≥3 seeded failure-scenario functional-acceptance run with human-reviewed evidence chains, regression check that Phases 1 and 2 still pass.
