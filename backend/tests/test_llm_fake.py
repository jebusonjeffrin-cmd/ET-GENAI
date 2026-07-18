from app.llm.fake import FakeLLMClient
from app.models.entities import EquipmentMention, ExtractedEntities


def test_fake_llm_returns_registered_response():
    llm = FakeLLMClient()
    llm.register_structured("hello", ExtractedEntities(equipment=[EquipmentMention(tag="P-101")]))
    result = llm.extract_structured("hello world", ExtractedEntities)
    assert result.equipment[0].tag == "P-101"


def test_fake_llm_synthesizes_fallback_when_unregistered():
    llm = FakeLLMClient()
    result = llm.extract_structured("no fixture registered for this", ExtractedEntities)
    assert isinstance(result, ExtractedEntities)
    assert result.equipment == []


def test_fake_llm_embed_is_deterministic():
    llm = FakeLLMClient()
    v1 = llm.embed(["same text"])
    v2 = llm.embed(["same text"])
    assert v1 == v2


def test_fake_llm_embed_differs_for_different_text():
    llm = FakeLLMClient()
    v1 = llm.embed(["text a"])
    v2 = llm.embed(["text b"])
    assert v1 != v2


def test_fake_llm_chat_stream_returns_registered_response():
    from app.llm.base import Message

    llm = FakeLLMClient()
    llm.register_chat("weather", "It's sunny.")
    chunks = list(llm.chat_stream([Message(role="user", content="what's the weather?")]))
    assert "".join(chunks) == "It's sunny."


def test_fake_llm_chat_returns_registered_text_response():
    from app.llm.base import Message

    llm = FakeLLMClient()
    llm.register_chat("weather", "It's sunny.")
    response = llm.chat([Message(role="user", content="what's the weather?")])
    assert response.content == "It's sunny."
    assert response.tool_calls == []


def test_fake_llm_chat_sequence_advances_per_call():
    from app.llm.base import ChatResponse, Message, ToolCall

    llm = FakeLLMClient()
    llm.register_chat_sequence(
        "investigate P-101",
        [
            ChatResponse(content="", tool_calls=[ToolCall(id="1", name="lookup", arguments={"tag": "P-101"})]),
            ChatResponse(content="Root cause: bearing wear.", tool_calls=[]),
        ],
    )

    first = llm.chat([Message(role="user", content="investigate P-101 failure")])
    assert first.tool_calls[0].name == "lookup"

    second = llm.chat(
        [
            Message(role="user", content="investigate P-101 failure"),
            Message(role="tool", content="{}"),
        ]
    )
    assert second.content == "Root cause: bearing wear."
    assert second.tool_calls == []


def test_fake_llm_chat_sequence_stays_on_last_response_once_exhausted():
    from app.llm.base import ChatResponse, Message

    llm = FakeLLMClient()
    llm.register_chat_sequence("done scenario", [ChatResponse(content="final", tool_calls=[])])

    first = llm.chat([Message(role="user", content="done scenario")])
    second = llm.chat([Message(role="user", content="done scenario")])
    assert first.content == second.content == "final"
