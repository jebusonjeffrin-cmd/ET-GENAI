from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import get_rca_agent
from app.rca.agent import RCAAgent, RCAResult

router = APIRouter(prefix="/rca", tags=["rca"])


class InvestigateRequest(BaseModel):
    description: str


class EvidenceOut(BaseModel):
    tool: str
    arguments: dict
    result_summary: str


class InvestigateResponse(BaseModel):
    root_cause_chain: str
    evidence: list[EvidenceOut]


def _to_response(result: RCAResult) -> InvestigateResponse:
    return InvestigateResponse(
        root_cause_chain=result.root_cause_chain,
        evidence=[
            EvidenceOut(tool=e.tool, arguments=e.arguments, result_summary=e.result_summary) for e in result.evidence
        ],
    )


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate(request: InvestigateRequest, agent: RCAAgent = Depends(get_rca_agent)) -> InvestigateResponse:
    result = agent.investigate(request.description)
    return _to_response(result)
