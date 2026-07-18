from app.retrieval.hybrid import HybridRetriever
from app.stores.graph_store import GraphEdge, GraphNode
from app.stores.vector_store import VectorRecord


def test_retrieve_finds_vector_match(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    text = "Pump P-101 vibration alarm"
    vector = fake_llm.embed([text])[0]
    fake_vector_store.upsert(VectorRecord(id="doc-1:0", document_id="doc-1", text=text, vector=vector))

    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    results = retriever.retrieve(text)

    assert any(r.chunk_id == "doc-1:0" for r in results)


def test_retrieve_finds_keyword_match(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    fake_keyword_store.index(
        VectorRecord(id="doc-2:0", document_id="doc-2", text="Valve V-200 seal inspection interval", vector=[])
    )

    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    results = retriever.retrieve("seal inspection interval")

    assert any(r.chunk_id == "doc-2:0" and r.source == "keyword" for r in results)


def test_retrieve_merges_vector_and_keyword_hit_on_same_chunk(
    fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store
):
    text = "Compressor C-305 bearing temperature elevated"
    vector = fake_llm.embed([text])[0]
    record = VectorRecord(id="doc-3:0", document_id="doc-3", text=text, vector=vector)
    fake_vector_store.upsert(record)
    fake_keyword_store.index(record)

    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    results = retriever.retrieve(text)

    matches = [r for r in results if r.chunk_id == "doc-3:0"]
    assert len(matches) == 1
    assert matches[0].source == "vector+keyword"


def test_retrieve_expands_via_equipment_tag_in_graph(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    # Document mentions P-101 in the graph but has no vector/keyword chunk
    # indexed — only the one-hop graph expansion should surface it.
    fake_graph_store.upsert_node(GraphNode(id="Document:doc-9", label="Document", properties={"filename": "wo.txt"}))
    fake_graph_store.upsert_node(GraphNode(id="Equipment:P-101", label="Equipment", properties={"tag": "P-101"}))
    fake_graph_store.upsert_edge(
        GraphEdge(source_id="Document:doc-9", target_id="Equipment:P-101", relationship="MENTIONS")
    )

    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    results = retriever.retrieve("What happened with P-101?")

    graph_hits = [r for r in results if r.source == "graph"]
    assert any(r.document_id == "doc-9" for r in graph_hits)


def test_retrieve_does_not_duplicate_document_already_found_by_vector_or_keyword(
    fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store
):
    fake_keyword_store.index(
        VectorRecord(id="doc-9:0", document_id="doc-9", text="Pump P-101 details", vector=[])
    )
    fake_graph_store.upsert_node(GraphNode(id="Document:doc-9", label="Document", properties={"filename": "wo.txt"}))
    fake_graph_store.upsert_node(GraphNode(id="Equipment:P-101", label="Equipment", properties={"tag": "P-101"}))
    fake_graph_store.upsert_edge(
        GraphEdge(source_id="Document:doc-9", target_id="Equipment:P-101", relationship="MENTIONS")
    )

    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    results = retriever.retrieve("Pump P-101 details")

    doc9_hits = [r for r in results if r.document_id == "doc-9"]
    assert len(doc9_hits) == 1
    assert doc9_hits[0].source == "keyword"


def test_retrieve_returns_empty_for_no_matches(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    assert retriever.retrieve("anything at all") == []
