from app.models.entities import EquipmentMention, ExtractedEntities


async def test_ask_endpoint_returns_answer_with_citations(client, fake_llm):
    fake_llm.register_structured(
        "Pump P-101",
        ExtractedEntities(equipment=[EquipmentMention(tag="P-101")], document_type="work_order"),
    )
    files = {"file": ("wo.txt", b"Work order: Pump P-101 bearing replaced by R. Iyer.", "text/plain")}
    upload_response = await client.post("/documents", files=files)
    document_id = upload_response.json()["id"]

    fake_llm.register_chat("QUESTION: Who worked on P-101?", "R. Iyer worked on it. [1]")

    response = await client.post("/copilot/ask", json={"question": "Who worked on P-101?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "R. Iyer worked on it. [1]"
    assert len(body["citations"]) == 1
    assert body["citations"][0]["document_id"] == document_id


async def test_ask_endpoint_with_empty_corpus_still_responds(client):
    response = await client.post("/copilot/ask", json={"question": "anything"})
    assert response.status_code == 200
    assert response.json()["citations"] == []


async def test_ask_endpoint_rejects_missing_question(client):
    response = await client.post("/copilot/ask", json={})
    assert response.status_code == 422
