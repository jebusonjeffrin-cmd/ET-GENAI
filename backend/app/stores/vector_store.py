from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class VectorRecord:
    id: str
    document_id: str
    text: str
    vector: list[float]
    metadata: dict = field(default_factory=dict)


class VectorStore(Protocol):
    def upsert(self, record: VectorRecord) -> None: ...
    def search(self, query_vector: list[float], top_k: int = 5) -> list[VectorRecord]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1e-9
    norm_b = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (norm_a * norm_b)


class FakeVectorStore:
    """In-memory cosine-similarity search. Backs every unit/integration test —
    no pgvector/Postgres required to run `pytest`. Good enough for hackathon
    corpus sizes. A real PgVectorStore is a Phase 1 hardening item, not yet
    built — tracked honestly in docs/PROJECT_PLAN.md, not hidden."""

    def __init__(self) -> None:
        self._records: list[VectorRecord] = []

    def upsert(self, record: VectorRecord) -> None:
        self._records.append(record)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[VectorRecord]:
        scored = sorted(self._records, key=lambda r: _cosine(r.vector, query_vector), reverse=True)
        return scored[:top_k]
