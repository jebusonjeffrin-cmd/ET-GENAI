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

---

## Phase 3 — Maintenance Intelligence & RCA Agent — done (2026-07-18)

### What was built

**LLM interface extension** (`app/llm/base.py`, `app/llm/fake.py`, `app/llm/ollama_client.py`)
- The Copilot's `chat_stream` (Phase 2) only streams text — it can't represent "the model wants a tool executed." Added a second method, `chat()`, that returns a `ChatResponse` (`content` + `tool_calls: list[ToolCall]`), i.e. a single non-streaming turn that can hand back either a final answer or a request to run tools. `OllamaLLMClient.chat()` parses Ollama's real `message.tool_calls` field; `FakeLLMClient.chat()` adds `register_chat_sequence(key, [ChatResponse, ...])` — scripts a multi-turn tool-calling conversation deterministically, advancing one response per call as the message history grows, so the whole agent loop is testable without a real model.

**Backend** (`backend/`)
- `RCATools` (`app/rca/tools.py`) — `search_equipment_history`, `get_work_orders`, `get_similar_incidents`. Deliberately **reuses** Phase 1's `GraphStore` and Phase 2's `HybridRetriever` rather than inventing a new WorkOrder/Incident data model — `get_work_orders` is just `search_equipment_history` filtered to `document_type == "work_order"`, and `get_similar_incidents` is the Copilot's own retriever. Less new code, less new risk, and it keeps the "one knowledge graph, one retrieval layer" story from `PROJECT_PLAN.md` §1 actually true.
- `RCAAgent` (`app/rca/agent.py`) — the tool-use loop: call the model, execute any requested tools, feed results back as `role: "tool"` messages, repeat until the model returns a final answer with no tool calls (or `max_iterations` is hit, at which point it's forced to conclude with whatever evidence it's gathered so far). Every tool call is recorded as an `EvidenceRef` (tool name, arguments, result) and returned alongside the root-cause chain — this is what makes the RCA output evidence-linked rather than a bare LLM opinion.
- `POST /rca/investigate` (`app/api/routes/rca.py`) — synchronous, returns `{root_cause_chain, evidence[]}`.
- Ingestion pipeline, dependencies, and stores are all unchanged — Phase 3 is new orchestration on top of existing infrastructure, not new plumbing.
- `backend/scripts/phase_gate/phase_3.py` — seeds 3 synthetic failure scenarios (compressor bearing failure, pump seal leak, valve actuator failure), each with supporting work-order/inspection documents, then runs the real agent against each and prints the evidence-linked chain plus a human-review checklist. Not run yet (see gaps below).

**Frontend** (`frontend/`)
- Maintenance & RCA page: the RCA Workspace is now a real interactive form (incident description → `POST /rca/investigate` → root-cause chain + evidence list), replacing the static "C-305 seeded scenario" fixture. Equipment Health stays fixture — deliberately scoped out this pass; a real risk score needs a trained failure-prediction model, which `PROJECT_PLAN.md` §7 already flagged as out of scope for a hackathon corpus, not an oversight.

### Verification actually run

| Check | Result |
|---|---|
| Backend tests (`pytest`) | **49/49 passed** (17 Phase 1 + 17 Phase 2 + 15 new Phase 3 — zero regressions) |
| Backend lint (`ruff check .`) | **clean** (includes `scripts/phase_gate/phase_3.py`) |
| Backend types (`mypy app`) | **clean** |
| Backend coverage | **78%** — `app/rca/agent.py` and `app/rca/tools.py` both at **100%** |
| Frontend tests (`vitest run`) | **15/15 passed** (was 11 — added a full `Maintenance.test.tsx`, the first for that page) |
| Frontend types (`tsc --noEmit`) | **clean** |
| Frontend production build (`vite build`) | **succeeds** |

### Key decisions made this phase

- **`chat()` is separate from `chat_stream()`, not a replacement.** Copilot keeps streaming (better UX for a chat answer); RCA needs discrete turns it can inspect for tool calls before deciding what happens next. Two methods, one interface, both real code paths — not a shortcut taken to avoid touching Phase 2.
- **No new data model for work orders/incidents.** Tempting to add explicit `WorkOrder`/`Incident` entities per the ontology in `PROJECT_PLAN.md` §4, but everything needed already exists as `Document` nodes with a `document_type` property (set during Phase 1 extraction) — filtering on that property is simpler and just as correct at this corpus size. Revisit only if `document_type` filtering proves too coarse.
- **`FakeLLMClient.chat()` checks single-shot `register_chat` registrations against only the *last* message, before checking multi-turn `register_chat_sequence` registrations against the *full* history.** This lets a test override an in-progress scripted sequence with a targeted response (e.g. the agent's forced-conclusion prompt) without the ambiguity of two registries both matching the same call. Documented inline in `fake.py` — not an obvious ordering, worth remembering if this file gets touched again.
- **Evidence is recorded as `(tool, arguments, result_summary)` on every call, not just the final answer.** This is what makes an RCA response auditable — a reviewer (human or the Phase 3 gate script) can check each claim against the specific tool call that produced it, not just trust the model's prose.

### Known gaps / honest limitations carried forward

- Everything listed under Phase 0+1 and Phase 2 above still applies (`PgVectorStore`, OCR/vision, Celery worker state-sharing, `/copilot/stream` untested).
- **Phase 3's real functional-acceptance run has not happened.** `scripts/phase_gate/phase_3.py` is written and ready but needs `LLM_BACKEND=ollama` against real inference — this dev machine still doesn't have Ollama. All 49 passing tests verify the *logic* is correct against scripted responses; they do not verify that a real 4B model reliably chooses to call tools before answering, or that its root-cause reasoning is actually good. That's exactly what the gate script and its human-review checklist exist to check, on the Ollama laptop.
- Equipment Health Dashboard, Work Order Explorer (as its own screen), and Maintenance Schedule view remain fixture-only — only the RCA Workspace was wired this pass. `get_work_orders` exists and is tested, so wiring a real Work Order Explorer later is a frontend-only task, not a backend one.
- `RCAAgent.investigate()` calls `llm.chat()` synchronously inside an async FastAPI route (same pattern as `CopilotService.answer()` in Phase 2) — fine for the fake/demo path, but a real multi-tool-call Ollama investigation will block the event loop for several seconds per request. Acceptable for a single-user hackathon demo; would need to move to a thread pool or async client before any concurrent-user use.

### Next phase

All three core modules from `PROJECT_PLAN.md` §1 (Ingestion & Knowledge Graph, Expert Knowledge Copilot, Maintenance Intelligence & RCA Agent) now have working, tested backends wired to real frontend UI. Per §1, Compliance and Lessons Learned are cut and not planned. Remaining work is **Phase 4 — Demo readiness** per `PROJECT_PLAN.md` §7: seed one coherent plant's worth of demo data across all three modules (not the scattered per-phase fixtures used for testing), a performance pass, PWA offline-mode check, and running the three outstanding phase-gate scripts (`phase_1.py`, `phase_2.py`, `phase_3.py`) against real Ollama on the deployment laptop before this can honestly be called fully gated rather than unit-tested.
