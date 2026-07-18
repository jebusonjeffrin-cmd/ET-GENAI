from app.llm.base import ChatResponse, ToolCall
from app.models.entities import EquipmentMention, ExtractedEntities


async def test_investigate_endpoint_returns_root_cause_and_evidence(client, fake_llm):
    fake_llm.register_structured(
        "Compressor C-305",
        ExtractedEntities(equipment=[EquipmentMention(tag="C-305")], document_type="work_order"),
    )
    files = {"file": ("wo.txt", b"Work order: Compressor C-305 bearing replaced.", "text/plain")}
    await client.post("/documents", files=files)

    fake_llm.register_chat_sequence(
        "C-305 tripped",
        [
            ChatResponse(
                content="", tool_calls=[ToolCall(id="1", name="search_equipment_history", arguments={"tag": "C-305"})]
            ),
            ChatResponse(content="Root cause: bearing wear. [1]", tool_calls=[]),
        ],
    )

    response = await client.post("/rca/investigate", json={"description": "C-305 tripped on overcurrent."})

    assert response.status_code == 200
    body = response.json()
    assert body["root_cause_chain"] == "Root cause: bearing wear. [1]"
    assert len(body["evidence"]) == 1
    assert body["evidence"][0]["tool"] == "search_equipment_history"


async def test_investigate_endpoint_rejects_missing_description(client):
    response = await client.post("/rca/investigate", json={})
    assert response.status_code == 422


async def test_investigate_endpoint_with_no_matching_equipment(client):
    response = await client.post("/rca/investigate", json={"description": "Unrelated question with no tags."})
    assert response.status_code == 200
    assert "root_cause_chain" in response.json()
