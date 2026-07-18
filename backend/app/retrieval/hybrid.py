from __future__ import annotations

import re
from dataclasses import dataclass

from app.llm.base import LLMClient
from app.stores.graph_store import GraphStore
from app.stores.keyword_store import KeywordStore
from app.stores.vector_store import VectorStore

# Matches equipment tags in the ontology (docs/PROJECT_PLAN.md §4), e.g. P-101, V-200, C-305.
EQUIPMENT_TAG_PATTERN = re.compile(r"\b[A-Z]{1,3}-\d{2,4}\b")


@dataclass
class RetrievedChunk:
    document_id: str
    chunk_id: str
    text: str
    source: str  # "vector" | "keyword" | "vector+keyword" | "graph"
    score: float = 0.0


class HybridRetriever:
    """Phase 2 retrieval: vector similarity + keyword overlap + one-hop graph
    expansion from any equipment tag mentioned in the question. Every
    dependency is injected as an interface, so this is fully testable with
    Fake* stores and no Ollama/Neo4j/real search index running. See
    docs/TESTING.md."""

    def __init__(
        self,
        llm: LLMClient,
        vector_store: VectorStore,
        keyword_store: KeywordStore,
        graph_store: GraphStore,
    ) -> None:
        self.llm = llm
        self.vector_store = vector_store
        self.keyword_store = keyword_store
        self.graph_store = graph_store

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        chunks: dict[str, RetrievedChunk] = {}

        query_vector = self.llm.embed([query])[0]
        for record in self.vector_store.search(query_vector, top_k=top_k):
            chunks[record.id] = RetrievedChunk(record.document_id, record.id, record.text, "vector")

        for record, score in self.keyword_store.search(query, top_k=top_k):
            existing = chunks.get(record.id)
            if existing:
                existing.source = "vector+keyword"
                existing.score = max(existing.score, score)
            else:
                chunks[record.id] = RetrievedChunk(record.document_id, record.id, record.text, "keyword", score)

        known_doc_ids = {c.document_id for c in chunks.values()}
        for tag in EQUIPMENT_TAG_PATTERN.findall(query):
            result = self.graph_store.get_equipment_360(tag)
            for link in result["linked"]:
                node = link["node"]
                if node is None or node.label != "Document":
                    continue
                doc_id = node.id.split(":", 1)[1]
                if doc_id in known_doc_ids:
                    continue
                chunk_id = f"graph:{tag}:{doc_id}"
                filename = node.properties.get("filename", doc_id)
                chunks[chunk_id] = RetrievedChunk(
                    document_id=doc_id,
                    chunk_id=chunk_id,
                    text=f"[Document '{filename}' mentions equipment {tag}, per the knowledge graph]",
                    source="graph",
                )
                known_doc_ids.add(doc_id)

        # Vector/keyword hits first (they carry real chunk text), graph
        # expansion hits appended after as supplementary context.
        ranked = sorted(chunks.values(), key=lambda c: (c.source == "graph", -c.score))
        return ranked[: top_k * 2]
