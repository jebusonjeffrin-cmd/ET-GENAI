from __future__ import annotations

import re
from typing import Protocol

from app.stores.vector_store import VectorRecord


class KeywordStore(Protocol):
    def index(self, record: VectorRecord) -> None: ...
    def search(self, query: str, top_k: int = 5) -> list[tuple[VectorRecord, float]]: ...


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class FakeKeywordStore:
    """In-memory keyword search via token-overlap (Jaccard) scoring. Stands in
    for a real search engine (OpenSearch/BM25) — good enough for hackathon
    corpus sizes and requires no external service for tests. A real backend
    is a Phase 2 hardening item, same pattern as PgVectorStore in Phase 1 —
    tracked, not hidden."""

    def __init__(self) -> None:
        self._records: list[VectorRecord] = []

    def index(self, record: VectorRecord) -> None:
        self._records.append(record)

    def search(self, query: str, top_k: int = 5) -> list[tuple[VectorRecord, float]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []
        scored: list[tuple[VectorRecord, float]] = []
        for record in self._records:
            record_tokens = _tokenize(record.text)
            overlap = query_tokens & record_tokens
            if overlap:
                score = len(overlap) / len(query_tokens | record_tokens)
                scored.append((record, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
