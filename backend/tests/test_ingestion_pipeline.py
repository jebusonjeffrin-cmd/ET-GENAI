from app.ingestion.pipeline import IngestionPipeline
from app.models.db_models import DocumentRecord
from app.models.entities import EquipmentMention, ExtractedEntities, PersonMention
from app.stores.document_repo import DocumentRepository


async def test_pipeline_writes_graph_and_vectors(
    fake_llm, fake_graph_store, fake_vector_store, fake_keyword_store, fake_object_store, test_session
):
    document_repo = DocumentRepository(test_session)
    await document_repo.create(DocumentRecord(id="doc-1", filename="work_order.txt", status="queued"))

    fake_llm.register_structured(
        "Pump P-101",
        ExtractedEntities(
            equipment=[EquipmentMention(tag="P-101", type="centrifugal pump")],
            personnel=[PersonMention(name="R. Iyer", role="technician")],
            document_type="work_order",
        ),
    )

    pipeline = IngestionPipeline(
        fake_llm, fake_graph_store, fake_vector_store, fake_keyword_store, fake_object_store, document_repo
    )
    entities = await pipeline.run("doc-1", "work_order.txt", b"Work order for Pump P-101, performed by R. Iyer.")

    assert entities.equipment[0].tag == "P-101"

    result = fake_graph_store.get_equipment_360("P-101")
    assert result["equipment"].properties["tag"] == "P-101"
    assert any(link["relationship"] == "MENTIONS" for link in result["linked"])

    record = await document_repo.get("doc-1")
    assert record.status == "done"

    assert len(fake_vector_store._records) > 0
    assert len(fake_keyword_store._records) > 0
    assert fake_object_store.get("doc-1") == b"Work order for Pump P-101, performed by R. Iyer."


async def test_pipeline_marks_status_transitions(
    fake_llm, fake_graph_store, fake_vector_store, fake_keyword_store, fake_object_store, test_session
):
    document_repo = DocumentRepository(test_session)
    await document_repo.create(DocumentRecord(id="doc-2", filename="sop.txt", status="queued"))

    pipeline = IngestionPipeline(
        fake_llm, fake_graph_store, fake_vector_store, fake_keyword_store, fake_object_store, document_repo
    )
    await pipeline.run("doc-2", "sop.txt", b"Standard operating procedure text.")

    record = await document_repo.get("doc-2")
    assert record.status == "done"
    assert record.error is None


async def test_equipment_not_found_returns_empty(fake_graph_store):
    result = fake_graph_store.get_equipment_360("NONEXISTENT-999")
    assert result["equipment"] is None
    assert result["linked"] == []
