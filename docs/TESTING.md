# Inspiron — Testing Strategy

Companion to `PROJECT_PLAN.md` §6/§7 (the testing gate protocol). That document says *when* a phase is allowed to end. This document says *how* the tests behind that rule are actually built and run.

---

## The constraint this strategy solves

Ollama runs on a different machine than the one used for development. Every test on the dev machine must work without a real Ollama instance present. Every phase-gate functional-acceptance check still needs real inference, so it runs wherever Ollama actually is.

## The `LLMClient` abstraction (build this first, in Phase 1, before anything else touches the model)

```python
class LLMClient(Protocol):
    def extract_structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...
    def chat_stream(self, messages: list[Message], tools: list[Tool] | None = None) -> Iterator[str]: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

- **`FakeLLMClient`** — returns deterministic, fixture-based responses. Used in all unit tests, all integration tests, and CI. Never makes a network call.
- **`OllamaLLMClient`** — the real adapter. Talks to `OLLAMA_HOST` (env var). Used only for phase-gate functional-acceptance runs and eventual production use.

**Rule:** nothing outside these two classes imports Ollama's client directly. Every service, route, and Celery task depends on `LLMClient`, never on `OllamaLLMClient` or `ollama` the package. This is what makes 90%+ of the codebase testable on a machine with no Ollama installed.

---

## Test pyramid

| Layer | Runs where | LLM used | Tools |
|---|---|---|---|
| Unit | Dev machine + CI | `FakeLLMClient` | `pytest`, `pytest-asyncio` |
| Integration (API + DB) | Dev machine + CI | `FakeLLMClient` | `pytest` + `httpx.AsyncClient`, Postgres/Neo4j/Redis as service containers (docker-compose locally, GitHub Actions services in CI) |
| Functional acceptance (phase gate) | Ollama-equipped machine — or dev machine if `OLLAMA_HOST` reaches it over LAN | `OllamaLLMClient`, real | manual run of `backend/scripts/phase_gate/phase_<n>.py`, checklist in `PROJECT_PLAN.md` §7 |
| Frontend | Dev machine + CI | n/a (mocked API responses via MSW) | Vitest + React Testing Library |

## What CI can and can't verify

`.github/workflows/ci.yml` runs unit + integration tests on every push/PR. GitHub Actions runners have no GPU and no Ollama, so **CI can never run the functional-acceptance phase-gate checks** — those are inherently manual, run against real inference, on whichever machine reaches Ollama. Treat a green CI run as "the logic is correct against known inputs," not as "the phase is done." Only the phase-gate checklist in `PROJECT_PLAN.md` §7 determines that.

## Running tests locally

```bash
# Backend
cd backend
pytest                                    # unit + integration — no Ollama needed
LLM_BACKEND=ollama python scripts/phase_gate/phase_1.py   # functional acceptance — requires a real Ollama instance
LLM_BACKEND=ollama python scripts/phase_gate/phase_2.py   # (phase_3.py likewise)

# Frontend
cd frontend
npm run test
```

## Bug-fix loop (per PROJECT_PLAN.md §6, step 4)

1. A test fails → log it (what broke, expected vs. actual).
2. Fix the root cause, not the test — unless the test itself was wrong.
3. Re-run the **full** suite, not just the failing test — a fix can break something else.
4. Re-run the previous phase's functional-acceptance check too (regression), not just this phase's.

## Coverage

70% line coverage on `backend/app` is a soft floor — a discipline marker to catch untested code paths, not a gate-blocker by itself. The functional-acceptance check is the real bar for "does this phase work."
