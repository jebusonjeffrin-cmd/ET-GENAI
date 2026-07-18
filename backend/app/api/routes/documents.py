from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict

from app.dependencies import (
    get_document_repo,
    get_graph_store,
    get_keyword_store,
    get_llm_client,
    get_object_store,
    get_vector_store,
)
from app.ingestion.pipeline import IngestionPipeline
from app.models.db_models import DocumentRecord
from app.stores.document_repo import DocumentRepository

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    status: str
    document_type: str


@router.post("", response_model=DocumentOut)
async def upload_document(
    file: UploadFile,
    llm=Depends(get_llm_client),
    graph_store=Depends(get_graph_store),
    vector_store=Depends(get_vector_store),
    keyword_store=Depends(get_keyword_store),
    object_store=Depends(get_object_store),
    document_repo: DocumentRepository = Depends(get_document_repo),
) -> DocumentOut:
    data = await file.read()
    document_id = str(uuid.uuid4())
    filename = file.filename or f"unnamed-{document_id[:8]}"
    await document_repo.create(DocumentRecord(id=document_id, filename=filename, status="queued"))

    pipeline = IngestionPipeline(llm, graph_store, vector_store, keyword_store, object_store, document_repo)
    entities = await pipeline.run(document_id, filename, data)

    record = await document_repo.get(document_id)
    if record is None:
        raise HTTPException(status_code=500, detail="Document vanished mid-ingestion")
    record.document_type = entities.document_type
    await document_repo.session.commit()
    await document_repo.session.refresh(record)
    return DocumentOut.model_validate(record)


@router.get("", response_model=list[DocumentOut])
async def list_documents(document_repo: DocumentRepository = Depends(get_document_repo)) -> list[DocumentOut]:
    records = await document_repo.list()
    return [DocumentOut.model_validate(r) for r in records]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, document_repo: DocumentRepository = Depends(get_document_repo)) -> DocumentOut:
    record = await document_repo.get(document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentOut.model_validate(record)
