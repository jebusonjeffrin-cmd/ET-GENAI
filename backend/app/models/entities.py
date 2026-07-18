from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class EquipmentMention(BaseModel):
    tag: str = Field(description="Equipment tag as written in the document, e.g. P-101")
    type: str = Field(default="", description="Equipment type if stated, e.g. centrifugal pump")


class PersonMention(BaseModel):
    name: str
    role: str = Field(default="")


class ProcessParameterMention(BaseModel):
    name: str
    value: str = Field(default="")
    unit: str = Field(default="")


class ExtractedEntities(BaseModel):
    """What Phase 1 extraction produces per document — matches the ontology in
    docs/PROJECT_PLAN.md §4."""

    equipment: list[EquipmentMention] = Field(default_factory=list)
    personnel: list[PersonMention] = Field(default_factory=list)
    process_parameters: list[ProcessParameterMention] = Field(default_factory=list)
    dates_mentioned: list[str] = Field(default_factory=list)
    document_type: str = Field(default="unknown", description="e.g. work_order, sop, pid, inspection_report")
    summary: str = Field(default="")


class IngestionStatus(StrEnum):
    QUEUED = "queued"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    WRITING_GRAPH = "writing_graph"
    EMBEDDING = "embedding"
    DONE = "done"
    FAILED = "failed"
