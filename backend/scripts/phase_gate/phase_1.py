"""Phase 1 functional-acceptance check — run manually on the machine that
reaches a real Ollama instance. Not run by CI or `pytest` (no GPU there).
See docs/TESTING.md and docs/PROJECT_PLAN.md §7.

Ingests a handful of fixture documents through the real pipeline against the
real model, then checks that equipment tags were extracted and the graph
traversal returns the expected linked records. This is a starter set — the
actual Phase 1 gate calls for 20+ varied documents; extend FIXTURE_DOCS
before treating this as a completed sign-off.

Usage:
    cd backend
    LLM_BACKEND=ollama OLLAMA_HOST=http://localhost:11434 python scripts/phase_gate/phase_1.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import get_settings  # noqa: E402
from app.ingestion.pipeline import IngestionPipeline  # noqa: E402
from app.models.db_models import DocumentRecord  # noqa: E402
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

EXPECTED_TAGS = ["P-101", "V-200", "C-305"]


async def main() -> None:
    settings = get_settings()
    if settings.llm_backend != "ollama":
        print("Set LLM_BACKEND=ollama before running this script — it exists to test against real inference.")
        raise SystemExit(1)

    from app.llm.ollama_client import OllamaLLMClient

    llm = OllamaLLMClient()
    graph_store = FakeGraphStore()

    await init_db()
    async with SessionLocal() as session:
        document_repo = DocumentRepository(session)
        pipeline = IngestionPipeline(llm, graph_store, FakeVectorStore(), FakeKeywordStore(), FakeObjectStore(), document_repo)
        for filename, text in FIXTURE_DOCS:
            await document_repo.create(DocumentRecord(id=filename, filename=filename, status="queued"))
            entities = await pipeline.run(filename, filename, text.encode())
            print(f"ingested {filename}: extracted equipment {[e.tag for e in entities.equipment]}")

    print("\nGraph traversal check:")
    passed = 0
    for tag in EXPECTED_TAGS:
        result = graph_store.get_equipment_360(tag)
        found = result["equipment"] is not None and len(result["linked"]) > 0
        print(f"  {tag}: {'PASS' if found else 'FAIL — not found or no linked document'}")
        if found:
            passed += 1

    print(f"\n{passed}/{len(EXPECTED_TAGS)} equipment tags correctly extracted and graph-linked.")
    print("Human review still required: confirm extraction accuracy against the source text, not just presence.")


if __name__ == "__main__":
    asyncio.run(main())
