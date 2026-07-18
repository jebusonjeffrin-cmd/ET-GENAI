from app.rca.tools import RCATools
from app.retrieval.hybrid import HybridRetriever
from app.stores.graph_store import GraphEdge, GraphNode
from app.stores.vector_store import VectorRecord


def _make_tools(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store) -> RCATools:
    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    return RCATools(fake_graph_store, retriever)


def test_search_equipment_history_returns_linked_records(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    fake_graph_store.upsert_node(GraphNode(id="Equipment:P-101", label="Equipment", properties={"tag": "P-101"}))
    fake_graph_store.upsert_node(
        GraphNode(id="Document:doc-1", label="Document", properties={"filename": "wo.txt", "document_type": "work_order"})
    )
    fake_graph_store.upsert_edge(GraphEdge(source_id="Document:doc-1", target_id="Equipment:P-101", relationship="MENTIONS"))

    tools = _make_tools(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    result = tools.search_equipment_history("P-101")

    assert result["equipment"]["properties"]["tag"] == "P-101"
    assert len(result["linked"]) == 1
    assert result["linked"][0]["node"]["properties"]["document_type"] == "work_order"


def test_search_equipment_history_returns_none_for_unknown_tag(
    fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store
):
    tools = _make_tools(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    result = tools.search_equipment_history("NONEXISTENT-999")
    assert result["equipment"] is None
    assert result["linked"] == []


def test_get_work_orders_filters_to_work_order_documents_only(
    fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store
):
    fake_graph_store.upsert_node(GraphNode(id="Equipment:C-305", label="Equipment", properties={"tag": "C-305"}))
    fake_graph_store.upsert_node(
        GraphNode(id="Document:wo-1", label="Document", properties={"filename": "wo.txt", "document_type": "work_order"})
    )
    fake_graph_store.upsert_node(
        GraphNode(id="Document:sop-1", label="Document", properties={"filename": "sop.txt", "document_type": "sop"})
    )
    fake_graph_store.upsert_edge(GraphEdge(source_id="Document:wo-1", target_id="Equipment:C-305", relationship="MENTIONS"))
    fake_graph_store.upsert_edge(GraphEdge(source_id="Document:sop-1", target_id="Equipment:C-305", relationship="MENTIONS"))

    tools = _make_tools(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    work_orders = tools.get_work_orders("C-305")

    assert len(work_orders) == 1
    assert work_orders[0]["node"]["id"] == "Document:wo-1"


def test_get_similar_incidents_uses_hybrid_retrieval(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    fake_keyword_store.index(
        VectorRecord(id="doc-2:0", document_id="doc-2", text="Compressor bearing temperature elevated", vector=[])
    )

    tools = _make_tools(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    results = tools.get_similar_incidents("bearing temperature elevated")

    assert any(r["document_id"] == "doc-2" for r in results)


def test_as_tool_definitions_exposes_all_three_tools(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    tools = _make_tools(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    names = {t.name for t in tools.as_tool_definitions()}
    assert names == {"search_equipment_history", "get_work_orders", "get_similar_incidents"}
