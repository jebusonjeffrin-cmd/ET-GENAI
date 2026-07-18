from __future__ import annotations

from app.ingestion.parsing import extract_text
from app.llm.base import LLMClient
from app.models.entities import ExtractedEntities, IngestionStatus
from app.stores.document_repo import DocumentRepository
from app.stores.graph_store import GraphEdge, GraphNode, GraphStore
from app.stores.keyword_store import KeywordStore
from app.stores.object_store import ObjectStore
from app.stores.vector_store import VectorRecord, VectorStore

EXTRACTION_PROMPT_TEMPLATE = """Extract equipment tags, personnel, process parameters,
and mentioned dates from the following industrial document. Classify the document type
(work_order, sop, pid, inspection_report, or unknown).

DOCUMENT:
{text}
"""


class IngestionPipeline:
    """Phase 1 core: upload -> parse -> extract -> write graph -> embed ->
    vector store. Every dependency is injected as an interface (LLMClient,
    GraphStore, VectorStore, ObjectStore), so this class is fully testable
    with Fake* implementations and zero external services running. See
    docs/TESTING.md."""

    def __init__(
        self,
        llm: LLMClient,
        graph_store: GraphStore,
        vector_store: VectorStore,
        keyword_store: KeywordStore,
        object_store: ObjectStore,
        document_repo: DocumentRepository,
    ) -> None:
        self.llm = llm
        self.graph_store = graph_store
        self.vector_store = vector_store
        self.keyword_store = keyword_store
        self.object_store = object_store
        self.document_repo = document_repo

    async def run(self, document_id: str, filename: str, data: bytes) -> ExtractedEntities:
        self.object_store.put(document_id, data)

        await self.document_repo.update_status(document_id, IngestionStatus.PARSING.value)
        text = extract_text(filename, data)

        await self.document_repo.update_status(document_id, IngestionStatus.EXTRACTING.value)
        entities = self.llm.extract_structured(
            EXTRACTION_PROMPT_TEMPLATE.format(text=text[:8000]),
            ExtractedEntities,
        )

        await self.document_repo.update_status(document_id, IngestionStatus.WRITING_GRAPH.value)
        self._write_graph(document_id, filename, entities)

        await self.document_repo.update_status(document_id, IngestionStatus.EMBEDDING.value)
        self._index_chunks(document_id, text)

        await self.document_repo.update_status(document_id, IngestionStatus.DONE.value)
        return entities

    def _write_graph(self, document_id: str, filename: str, entities: ExtractedEntities) -> None:
        doc_node_id = f"Document:{document_id}"
        self.graph_store.upsert_node(
            GraphNode(
                id=doc_node_id,
                label="Document",
                properties={"filename": filename, "document_type": entities.document_type},
            )
        )
        for eq in entities.equipment:
            eq_node_id = f"Equipment:{eq.tag}"
            eq_props = {"tag": eq.tag, "type": eq.type}
            self.graph_store.upsert_node(GraphNode(id=eq_node_id, label="Equipment", properties=eq_props))
            self.graph_store.upsert_edge(GraphEdge(source_id=doc_node_id, target_id=eq_node_id, relationship="MENTIONS"))
        for person in entities.personnel:
            person_node_id = f"Person:{person.name}"
            person_props = {"name": person.name, "role": person.role}
            self.graph_store.upsert_node(GraphNode(id=person_node_id, label="Person", properties=person_props))
            self.graph_store.upsert_edge(GraphEdge(source_id=doc_node_id, target_id=person_node_id, relationship="MENTIONS"))

    def _index_chunks(self, document_id: str, text: str) -> None:
        chunks = _chunk(text)
        if not chunks:
            return
        vectors = self.llm.embed(chunks)
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            record = VectorRecord(id=f"{document_id}:{i}", document_id=document_id, text=chunk, vector=vector)
            self.vector_store.upsert(record)
            self.keyword_store.index(record)


def _chunk(text: str, size: int = 1000, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks
