"""Phase 2 functional-acceptance check — run manually on the machine that
reaches a real Ollama instance. Not run by CI or `pytest` (no GPU there).
See docs/TESTING.md and docs/PROJECT_PLAN.md §7.

Ingests a small fixture corpus through the real pipeline, then runs a
benchmark question set through the real Copilot service and reports whether
each answer carried at least one citation. This is a starter set of 5
questions covering the 3 seeded documents — the actual Phase 2 gate calls
for >=15 domain-expert questions against the real Phase 1 corpus; extend
BENCHMARK_QUESTIONS (and point at real ingested data, not this fixture set)
before treating this as a completed sign-off.

Usage:
    cd backend
    LLM_BACKEND=ollama OLLAMA_HOST=http://localhost:11434 python scripts/phase_gate/phase_2.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import get_settings  # noqa: E402
from app.copilot.service import CopilotService  # noqa: E402
from app.ingestion.pipeline import IngestionPipeline  # noqa: E402
from app.models.db_models import DocumentRecord  # noqa: E402
from app.retrieval.hybrid import HybridRetriever  # noqa: E402
from app.stores.document_repo import DocumentRepository, SessionLocal, init_db  # noqa: E402
from app.stores.graph_store import FakeGraphStore  # noqa: E402
from app.stores.keyword_store import FakeKeywordStore  # noqa: E402
from app.stores.object_store import FakeObjectStore  # noqa: E402
from app.stores.vector_store import FakeVectorStore  # noqa: E402

FIXTURE_DOCS = [
    (
        "work_order_p101.txt",
        "Work order WO-4521: replaced bearing on Pump P-101 due to vibration alarm. Performed by R. Iyer on 2026-03-12.",
    ),
    (
        "sop_v200.txt",
        "Standard Operating Procedure for Valve V-200: inspect seal integrity every 6 months per OEM guidance.",
    ),
    (
        "inspection_c305.txt",
        "Inspection report: Compressor C-305 showed elevated bearing temperature. Recommend follow-up within 30 days.",
    ),
]

BENCHMARK_QUESTIONS = [
    "Who performed the work order on Pump P-101?",
    "What was replaced on Pump P-101, and why?",
    "How often should Valve V-200's seal be inspected?",
    "What issue was found on Compressor C-305?",
    "Is there a recommended follow-up for Compressor C-305, and by when?",
]


async def main() -> None:
    settings = get_settings()
    if settings.llm_backend != "ollama":
        print("Set LLM_BACKEND=ollama before running this script — it exists to test against real inference.")
        raise SystemExit(1)

    from app.llm.ollama_client import OllamaLLMClient

    llm = OllamaLLMClient()
    graph_store = FakeGraphStore()
    vector_store = FakeVectorStore()
    keyword_store = FakeKeywordStore()

    await init_db()
    async with SessionLocal() as session:
        document_repo = DocumentRepository(session)
        pipeline = IngestionPipeline(llm, graph_store, vector_store, keyword_store, FakeObjectStore(), document_repo)
        for filename, text in FIXTURE_DOCS:
            await document_repo.create(DocumentRecord(id=filename, filename=filename, status="queued"))
            await pipeline.run(filename, filename, text.encode())
            print(f"ingested {filename}")

    retriever = HybridRetriever(llm, vector_store, keyword_store, graph_store)
    service = CopilotService(llm, retriever)

    print("\nBenchmark run:")
    passed = 0
    total_latency = 0.0
    for question in BENCHMARK_QUESTIONS:
        start = time.monotonic()
        result = service.answer(question)
        elapsed = time.monotonic() - start
        total_latency += elapsed

        has_citation = len(result.citations) > 0
        status = "PASS" if has_citation else "FAIL (no citation)"
        if has_citation:
            passed += 1
        print(f"\nQ: {question}\nA: {result.answer}\n{status} — {elapsed:.2f}s")

    avg_latency = total_latency / len(BENCHMARK_QUESTIONS)
    print(f"\n{passed}/{len(BENCHMARK_QUESTIONS)} answers included at least one citation.")
    print(f"Average time-to-answer: {avg_latency:.2f}s (compare against the manual-search baseline per PROJECT_PLAN.md §7).")
    print("Human review still required: verify each cited source actually supports the claim, not just that a citation exists.")


if __name__ == "__main__":
    asyncio.run(main())
