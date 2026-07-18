from app.llm.base import ChatResponse, ToolCall
from app.rca.agent import RCAAgent
from app.rca.tools import RCATools
from app.retrieval.hybrid import HybridRetriever
from app.stores.graph_store import GraphEdge, GraphNode


def _make_agent(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store, max_iterations: int = 5) -> RCAAgent:
    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    tools = RCATools(fake_graph_store, retriever)
    return RCAAgent(fake_llm, tools, max_iterations=max_iterations)


def test_agent_gathers_evidence_before_concluding(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    fake_graph_store.upsert_node(GraphNode(id="Equipment:C-305", label="Equipment", properties={"tag": "C-305"}))
    fake_graph_store.upsert_node(
        GraphNode(id="Document:wo-1", label="Document", properties={"filename": "wo.txt", "document_type": "work_order"})
    )
    fake_graph_store.upsert_edge(GraphEdge(source_id="Document:wo-1", target_id="Equipment:C-305", relationship="MENTIONS"))

    agent = _make_agent(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)

    fake_llm.register_chat_sequence(
        "Compressor C-305 tripped",
        [
            ChatResponse(
                content="", tool_calls=[ToolCall(id="1", name="search_equipment_history", arguments={"tag": "C-305"})]
            ),
            ChatResponse(content="", tool_calls=[ToolCall(id="2", name="get_work_orders", arguments={"tag": "C-305"})]),
            ChatResponse(content="Root cause: bearing wear caused the overcurrent trip. [wo-1]", tool_calls=[]),
        ],
    )

    result = agent.investigate("Compressor C-305 tripped on overcurrent during startup.")

    assert result.root_cause_chain == "Root cause: bearing wear caused the overcurrent trip. [wo-1]"
    assert len(result.evidence) == 2
    assert result.evidence[0].tool == "search_equipment_history"
    assert result.evidence[1].tool == "get_work_orders"
    assert result.evidence[0].arguments == {"tag": "C-305"}


def test_agent_returns_immediately_when_no_tool_calls(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    agent = _make_agent(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)

    fake_llm.register_chat("trivial question", "No investigation needed.")

    result = agent.investigate("trivial question")
    assert result.root_cause_chain == "No investigation needed."
    assert result.evidence == []


def test_agent_handles_unknown_tool_gracefully(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    agent = _make_agent(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)

    fake_llm.register_chat_sequence(
        "mystery failure",
        [
            ChatResponse(content="", tool_calls=[ToolCall(id="1", name="not_a_real_tool", arguments={})]),
            ChatResponse(content="Could not determine root cause.", tool_calls=[]),
        ],
    )

    result = agent.investigate("mystery failure")
    assert result.evidence[0].tool == "not_a_real_tool"
    assert "error" in result.evidence[0].result_summary


def test_agent_forces_conclusion_after_max_iterations(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    agent = _make_agent(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store, max_iterations=2)

    fake_llm.register_chat_sequence(
        "endless loop scenario",
        [
            ChatResponse(
                content="", tool_calls=[ToolCall(id="1", name="search_equipment_history", arguments={"tag": "X-1"})]
            ),
            ChatResponse(
                content="", tool_calls=[ToolCall(id="2", name="search_equipment_history", arguments={"tag": "X-1"})]
            ),
        ],
    )
    fake_llm.register_chat("Summarize your root-cause findings", "Forced summary due to iteration limit.")

    result = agent.investigate("endless loop scenario")

    assert result.root_cause_chain == "Forced summary due to iteration limit."
    assert len(result.evidence) == 2
