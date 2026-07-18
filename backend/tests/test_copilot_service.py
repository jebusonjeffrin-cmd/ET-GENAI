from app.copilot.service import CopilotService
from app.retrieval.hybrid import HybridRetriever
from app.stores.vector_store import VectorRecord


def test_answer_includes_citations_from_registered_chat_response(
    fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store
):
    text = "Pump P-101 bearing was replaced by R. Iyer"
    vector = fake_llm.embed([text])[0]
    fake_vector_store.upsert(VectorRecord(id="doc-1:0", document_id="doc-1", text=text, vector=vector))

    fake_llm.register_chat("QUESTION: Who replaced the bearing on P-101?", "R. Iyer replaced it. [1]")

    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    service = CopilotService(fake_llm, retriever)

    result = service.answer("Who replaced the bearing on P-101?")

    assert result.answer == "R. Iyer replaced it. [1]"
    assert len(result.citations) == 1
    assert result.citations[0].document_id == "doc-1"


def test_answer_with_no_citations_returns_empty_list(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store):
    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    service = CopilotService(fake_llm, retriever)

    result = service.answer("random question with nothing in the corpus")

    assert result.citations == []


def test_build_citations_ignores_out_of_range_indices(
    fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store
):
    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    service = CopilotService(fake_llm, retriever)

    citations = service.build_citations("See [1] and [5]", chunks=[])
    assert citations == []


def test_build_citations_deduplicates_repeated_markers(
    fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store
):
    from app.retrieval.hybrid import RetrievedChunk

    retriever = HybridRetriever(fake_llm, fake_vector_store, fake_keyword_store, fake_graph_store)
    service = CopilotService(fake_llm, retriever)
    chunks = [RetrievedChunk(document_id="doc-1", chunk_id="doc-1:0", text="...", source="vector")]

    citations = service.build_citations("As shown in [1], and again in [1].", chunks=chunks)
    assert len(citations) == 1
