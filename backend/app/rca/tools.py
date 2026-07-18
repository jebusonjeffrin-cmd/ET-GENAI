from __future__ import annotations

from app.llm.base import Tool
from app.retrieval.hybrid import HybridRetriever
from app.stores.graph_store import GraphNode, GraphStore


def _node_to_dict(node: GraphNode | None) -> dict | None:
    if node is None:
        return None
    return {"id": node.id, "label": node.label, "properties": node.properties}


class RCATools:
    """The evidence the RCA agent (Phase 3) can pull before drafting a
    root-cause chain. Reuses the same GraphStore and HybridRetriever built in
    Phase 1/2 — no new data model, no new infra. Every tool call is a plain
    method, fully testable in isolation with Fake* stores. See
    docs/TESTING.md."""

    def __init__(self, graph_store: GraphStore, retriever: HybridRetriever) -> None:
        self.graph_store = graph_store
        self.retriever = retriever

    def search_equipment_history(self, tag: str) -> dict:
        """Every document and person linked to an equipment tag in the
        knowledge graph — the closest thing this platform has to a single
        equipment record."""
        result = self.graph_store.get_equipment_360(tag)
        return {
            "equipment": _node_to_dict(result["equipment"]),
            "linked": [
                {"relationship": link["relationship"], "node": _node_to_dict(link["node"])}
                for link in result["linked"]
            ],
        }

    def get_work_orders(self, tag: str) -> list[dict]:
        """The subset of an equipment tag's linked documents classified as
        work orders during Phase 1 extraction."""
        history = self.search_equipment_history(tag)
        return [
            link
            for link in history["linked"]
            if link["node"] and link["node"]["properties"].get("document_type") == "work_order"
        ]

    def get_similar_incidents(self, description: str, top_k: int = 5) -> list[dict]:
        """Hybrid retrieval (vector + keyword + graph) over the ingested
        corpus for passages resembling the given incident description —
        reuses the Phase 2 Copilot's retriever verbatim."""
        chunks = self.retriever.retrieve(description, top_k=top_k)
        return [
            {"document_id": c.document_id, "chunk_id": c.chunk_id, "text": c.text, "source": c.source}
            for c in chunks
        ]

    def as_tool_definitions(self) -> list[Tool]:
        return [
            Tool(
                name="search_equipment_history",
                description="Get every document and person linked to an equipment tag in the knowledge graph.",
                parameters={
                    "type": "object",
                    "properties": {"tag": {"type": "string", "description": "Equipment tag, e.g. P-101"}},
                    "required": ["tag"],
                },
                handler=self.search_equipment_history,
            ),
            Tool(
                name="get_work_orders",
                description="Get the work-order documents linked to an equipment tag.",
                parameters={
                    "type": "object",
                    "properties": {"tag": {"type": "string", "description": "Equipment tag, e.g. P-101"}},
                    "required": ["tag"],
                },
                handler=self.get_work_orders,
            ),
            Tool(
                name="get_similar_incidents",
                description="Search the ingested corpus for passages resembling a described incident or failure.",
                parameters={
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "Free-text description of the incident"}
                    },
                    "required": ["description"],
                },
                handler=self.get_similar_incidents,
            ),
        ]
