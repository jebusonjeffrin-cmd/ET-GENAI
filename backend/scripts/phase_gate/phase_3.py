"""Phase 3 functional-acceptance check — run manually on the machine that
reaches a real Ollama instance. Not run by CI or `pytest` (no GPU there).
See docs/TESTING.md and docs/PROJECT_PLAN.md §7.

Seeds 3 synthetic failure scenarios (each with supporting work order and
inspection documents), then runs the real RCA agent against each and prints
the evidence-linked root-cause chain for human review. This is exactly the
Phase 3 gate as written: "the RCA agent must produce a root-cause chain
where every claim links to a real evidence record; a human reviewer
confirms the chain is plausible" — the human-review part cannot be
automated, so this script's job is to produce output a person can actually
review, not to self-certify a pass/fail.

Usage:
    cd backend
    LLM_BACKEND=ollama OLLAMA_HOST=http://localhost:11434 python scripts/phase_gate/phase_3.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import get_settings  # noqa: E402
from app.ingestion.pipeline import IngestionPipeline  # noqa: E402
from app.models.db_models import DocumentRecord  # noqa: E402
from app.rca.agent import RCAAgent  # noqa: E402
from app.rca.tools import RCATools  # noqa: E402
from app.retrieval.hybrid import HybridRetriever  # noqa: E402
from app.stores.document_repo import DocumentRepository, SessionLocal, init_db  # noqa: E402
from app.stores.graph_store import FakeGraphStore  # noqa: E402
from app.stores.keyword_store import FakeKeywordStore  # noqa: E402
from app.stores.object_store import FakeObjectStore  # noqa: E402
from app.stores.vector_store import FakeVectorStore  # noqa: E402

# Each scenario: supporting documents to ingest first, then the incident
# description the agent investigates. Extend this list before treating a run
# as a completed sign-off — 3 is the plan's stated minimum, not a target.
SCENARIOS = [
    {
        "docs": [
            (
                "wo_c305_1.txt",
                "Work order WO-7791: Compressor C-305 bearing replaced due to elevated vibration. "
                "Performed by A. Nair on 2026-01-02.",
            ),
            (
                "inspection_c305_1.txt",
                "Inspection report: Compressor C-305 last lubrication service was 14 months ago, "
                "exceeding the OEM-recommended 6-month interval.",
            ),
        ],
        "incident": "Compressor C-305 tripped on overcurrent during startup on 2026-01-04.",
    },
    {
        "docs": [
            (
                "wo_p101_1.txt",
                "Work order WO-4521: Pump P-101 seal replaced after leak detected during routine "
                "walkdown. Performed by R. Iyer on 2026-02-15.",
            ),
            (
                "sop_p101.txt",
                "Standard Operating Procedure for Pump P-101: seal inspection required every 3 "
                "months; last recorded inspection was 5 months prior to the leak.",
            ),
        ],
        "incident": "Pump P-101 is leaking process fluid at the mechanical seal.",
    },
    {
        "docs": [
            (
                "inspection_v200_1.txt",
                "Inspection report: Valve V-200 actuator showed intermittent failure to fully close "
                "during the March 2026 test cycle.",
            ),
            (
                "wo_v200_1.txt",
                "Work order WO-5310: Valve V-200 actuator solenoid replaced; root cause noted as "
                "moisture ingress in the actuator housing.",
            ),
        ],
        "incident": "Valve V-200 failed to close fully during an emergency shutdown drill.",
    },
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
        for scenario in SCENARIOS:
            for filename, text in scenario["docs"]:
                await document_repo.create(DocumentRecord(id=filename, filename=filename, status="queued"))
                await pipeline.run(filename, filename, text.encode())
                print(f"ingested {filename}")

    retriever = HybridRetriever(llm, vector_store, keyword_store, graph_store)
    tools = RCATools(graph_store, retriever)
    agent = RCAAgent(llm, tools)

    print("\n" + "=" * 70)
    print("RCA investigations — review each chain for plausibility by hand.")
    print("=" * 70)
    for i, scenario in enumerate(SCENARIOS, start=1):
        result = agent.investigate(scenario["incident"])
        print(f"\n--- Scenario {i} ---")
        print(f"Incident: {scenario['incident']}")
        print(f"\nRoot-cause chain:\n{result.root_cause_chain}")
        print(f"\nEvidence gathered ({len(result.evidence)} tool calls):")
        for e in result.evidence:
            print(f"  - {e.tool}({e.arguments}) -> {e.result_summary[:200]}")

    print("\n" + "=" * 70)
    print("Human review checklist per scenario:")
    print("  [ ] Root-cause chain is plausible given the ingested documents")
    print("  [ ] Every factual claim traces back to a real piece of evidence above")
    print("  [ ] Agent called at least one tool before concluding (not a guess)")


if __name__ == "__main__":
    asyncio.run(main())
