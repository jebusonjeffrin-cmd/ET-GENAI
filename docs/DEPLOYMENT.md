# Deployment Runbook — moving Inspiron to the Ollama laptop

Everything so far was built and tested on a machine with no Ollama, no GPU (`FakeLLMClient` stood in for real inference — see `docs/TESTING.md`). This runbook closes that gap: clone the repo onto the laptop that actually has Ollama, point the code at it, and run the three phase-gate scripts that have been sitting ready since Phase 1.

Follow the steps in order. Each one says what "done" looks like before moving to the next.

---

## 0. Prerequisites — confirm before starting

On the target laptop:

- [ ] `git --version` works
- [ ] `python --version` (or `python3`) shows 3.11+
- [ ] `node --version` shows 20+
- [ ] `ollama --version` works, and `ollama list` returns without error (Ollama is installed **and running**)

If `ollama list` errors, the Ollama service isn't running — start the Ollama app (Windows: it's a tray-icon background app after install) or run `ollama serve` in a terminal.

---

## 1. Clone the repo

```bash
git clone https://github.com/jebusonjeffrin-cmd/ET-GENAI.git
cd ET-GENAI
```

---

## 2. Confirm which model is actually pulled

```bash
ollama list
```

The code defaults to `gemma3:4b` (chat/extraction) and `nomic-embed-text` (embeddings). If they're not listed:

```bash
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

**If a different model is already there** (e.g. `qwen3:4b`, `llama3.2:3b`) — don't re-download anything, just write down its exact name (including the `:tag`). You'll put it in `.env` in step 4 instead of `gemma3:4b`.

---

## 3. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Git Bash on Windows; .venv\Scripts\activate.bat for cmd.exe; source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
```

Sanity check — proves the clone and install worked, **before** touching Ollama at all:

```bash
pytest
```

Expect `49 passed`. If this fails, it's an environment problem (Python version, missing dependency) — fix it here before going further; it has nothing to do with Ollama.

---

## 4. Point the backend at real Ollama

```bash
cp .env.example .env
```

Edit `backend/.env`:

```ini
LLM_BACKEND=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma3:4b            # overwrite with whatever step 2 actually found
OLLAMA_EMBED_MODEL=nomic-embed-text
```

Leave everything else at its default. `GRAPH_STORE_BACKEND=fake` and `DATABASE_URL=sqlite+...` mean **Neo4j and Postgres are not required** for anything in this runbook — that's optional hardening, covered in step 7.

---

## 5. Run the three phase-gate scripts — the actual point of this move

Every phase (`docs/PROGRESS.md`) has been unit-tested against `FakeLLMClient` but never run against a real model. These scripts close that:

```bash
python scripts/phase_gate/phase_1.py
python scripts/phase_gate/phase_2.py
python scripts/phase_gate/phase_3.py
```

What each one does and what to check:

| Script | Ingests | Then | You check |
|---|---|---|---|
| `phase_1.py` | 3 fixture documents | Prints extracted equipment tags + graph traversal results | Extraction accuracy against the source text |
| `phase_2.py` | Same 3 documents | Runs a 5-question benchmark through the Copilot, reports citation presence + time-to-answer | Whether each cited source actually supports the claim |
| `phase_3.py` | 3 failure scenarios (compressor, pump, valve) with supporting docs | Runs the RCA agent on each, prints the evidence-linked root-cause chain | Whether the chain is plausible and every claim traces to real evidence (checklist printed at the end) |

**Read the output** — these scripts print results, they don't self-certify pass/fail. The human-review step is the point; see `docs/TESTING.md` for why it can't be automated.

If a script exits immediately with `Set LLM_BACKEND=ollama before running this script` — `.env` wasn't picked up. Run from inside `backend/` with the var inline to confirm: `LLM_BACKEND=ollama python scripts/phase_gate/phase_1.py`.

---

## 6. Run it live

Backend:

```bash
uvicorn app.main:app --reload
```

Frontend (new terminal):

```bash
cd ../frontend
npm install
npm run dev
```

Open the printed `localhost:5173` URL. Document Library, Knowledge Graph Explorer, Copilot, and the RCA Workspace are now backed by real `gemma3:4b` inference — this is the actual product, not `FakeLLMClient`. Upload a document, ask the Copilot about it, run an RCA investigation.

**Note:** with `GRAPH_STORE_BACKEND=fake` (default), everything ingested lives in server memory — restarting `uvicorn` clears it. Fine for a demo session; step 7 covers persistence.

---

## 7. Optional: full stack with Postgres / Neo4j / Redis

Only needed for persistence across restarts, or to exercise the real `Neo4jGraphStore` adapter instead of the in-memory fake. Requires Docker Desktop.

```bash
cd ..   # repo root
docker compose up -d
```

`docker-compose.yml`'s `backend` service sets `GRAPH_STORE_BACKEND=neo4j` and a Postgres `DATABASE_URL` automatically, and loads `backend/.env` via `env_file` — so your `OLLAMA_*` settings from step 4 carry over (Ollama itself isn't containerized; the container reaches it on the host).

**Known gap, from `docs/PROGRESS.md`:** vector search stays in-memory (`FakeVectorStore`) even here — `PgVectorStore` was never built. Only the graph store becomes real in this configuration.

---

## 8. Push changes back

If step 5's output leads to a fix (a prompt tweak, a bug the real model surfaced that the fakes never would), commit and push as usual from here. `git push` still asks for confirmation, same as on the original dev machine.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Set LLM_BACKEND=ollama before running this script` | `.env` missing/not edited (step 4), or not running from `backend/` |
| Connection error talking to Ollama | Ollama service isn't running — `ollama list` should work standalone before debugging this repo |
| `model "X" not found` | `OLLAMA_MODEL` in `.env` doesn't exactly match `ollama list` output, including the `:tag` |
| A phase-gate script is very slow | Expected on a CPU-only laptop — no discrete GPU means a 4B model can take real time per call. `OllamaLLMClient` uses a 120s per-call timeout (`app/llm/ollama_client.py`); raise it if a call actually times out, don't assume it's broken just because it's slow |
| `pytest` fails here but passed on the original dev machine | Not a model issue — tests never touch Ollama. Check Python version and `pip install` output first |
