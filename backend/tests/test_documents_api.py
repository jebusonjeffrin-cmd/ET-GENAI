from app.models.entities import EquipmentMention, ExtractedEntities


async def test_upload_document_returns_done_status(client, fake_llm):
    fake_llm.register_structured(
        "Standard Operating Procedure",
        ExtractedEntities(equipment=[EquipmentMention(tag="V-200")], document_type="sop"),
    )

    files = {"file": ("sop.txt", b"Standard Operating Procedure for valve V-200 maintenance.", "text/plain")}
    response = await client.post("/documents", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["document_type"] == "sop"


async def test_list_documents(client):
    response = await client.get("/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_get_document_not_found(client):
    response = await client.get("/documents/does-not-exist")
    assert response.status_code == 404


async def test_equipment_360_endpoint(client, fake_llm):
    fake_llm.register_structured("Valve V-300", ExtractedEntities(equipment=[EquipmentMention(tag="V-300")]))
    files = {"file": ("inspection.txt", b"Inspection of Valve V-300 completed.", "text/plain")}
    await client.post("/documents", files=files)

    response = await client.get("/graph/equipment/V-300")
    assert response.status_code == 200
    assert response.json()["equipment"] is not None


async def test_graph_stats_endpoint(client, fake_llm):
    fake_llm.register_structured("Valve V-400", ExtractedEntities(equipment=[EquipmentMention(tag="V-400")]))
    files = {"file": ("inspection2.txt", b"Inspection of Valve V-400 completed.", "text/plain")}
    await client.post("/documents", files=files)

    response = await client.get("/graph/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["node_counts"].get("Equipment", 0) >= 1


async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
