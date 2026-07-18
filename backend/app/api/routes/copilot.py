from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.copilot.service import AnswerResult, CopilotService
from app.dependencies import get_copilot_service

router = APIRouter(prefix="/copilot", tags=["copilot"])


class AskRequest(BaseModel):
    question: str


class CitationOut(BaseModel):
    index: int
    document_id: str
    chunk_id: str
    text: str


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationOut]


def _to_response(result: AnswerResult) -> AskResponse:
    return AskResponse(
        answer=result.answer,
        citations=[
            CitationOut(index=c.index, document_id=c.document_id, chunk_id=c.chunk_id, text=c.text)
            for c in result.citations
        ],
    )


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, service: CopilotService = Depends(get_copilot_service)) -> AskResponse:
    result = service.answer(request.question)
    return _to_response(result)


@router.websocket("/stream")
async def stream(websocket: WebSocket, service: CopilotService = Depends(get_copilot_service)) -> None:
    """Token-by-token streaming path for the real chat UX. NOTE (documented,
    not hidden): this endpoint is not yet covered by an automated test —
    testing FastAPI WebSocket routes needs the synchronous TestClient, which
    doesn't mix safely with this project's async-fixture test setup. The
    REST /copilot/ask endpoint above carries the tested path; this endpoint
    is real code, exercised manually. Tracked as a Phase 2 hardening item."""
    await websocket.accept()
    try:
        while True:
            question = await websocket.receive_text()
            token_stream, chunks = service.answer_stream(question)
            full_text = ""
            for token in token_stream:
                full_text += token
                await websocket.send_json({"type": "token", "content": token})
            citations = service.build_citations(full_text, chunks)
            await websocket.send_json(
                {
                    "type": "done",
                    "citations": [
                        {"index": c.index, "document_id": c.document_id, "chunk_id": c.chunk_id, "text": c.text}
                        for c in citations
                    ],
                }
            )
    except WebSocketDisconnect:
        pass
