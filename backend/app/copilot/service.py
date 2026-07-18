from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

from app.llm.base import LLMClient, Message
from app.retrieval.hybrid import HybridRetriever, RetrievedChunk

SYSTEM_PROMPT = """You are Inspiron's Expert Knowledge Copilot, answering questions for
plant engineers and technicians using only the provided source excerpts. Cite every
factual claim with the bracketed source number it came from, e.g. [1]. If the sources
don't contain the answer, say so plainly — never invent equipment tags, dates, or
procedures that aren't in the provided sources."""

CITATION_PATTERN = re.compile(r"\[(\d+)\]")


@dataclass
class Citation:
    index: int
    document_id: str
    chunk_id: str
    text: str


@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation]


def _build_prompt(query: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return f"No sources were found in the knowledge base for this question.\n\nQUESTION: {query}"
    sources = "\n\n".join(f"[{i + 1}] (document {c.document_id})\n{c.text}" for i, c in enumerate(chunks))
    return f"SOURCES:\n{sources}\n\nQUESTION: {query}"


class CopilotService:
    """Phase 2 core: retrieve -> synthesize with citations. Fully testable
    with FakeLLMClient + Fake* stores — no Ollama required. See
    docs/TESTING.md."""

    def __init__(self, llm: LLMClient, retriever: HybridRetriever) -> None:
        self.llm = llm
        self.retriever = retriever

    def answer_stream(self, query: str, top_k: int = 5) -> tuple[Iterator[str], list[RetrievedChunk]]:
        chunks = self.retriever.retrieve(query, top_k=top_k)
        prompt = _build_prompt(query, chunks)
        messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=prompt)]
        return self.llm.chat_stream(messages), chunks

    def answer(self, query: str, top_k: int = 5) -> AnswerResult:
        stream, chunks = self.answer_stream(query, top_k=top_k)
        text = "".join(stream)
        return AnswerResult(answer=text, citations=self.build_citations(text, chunks))

    def build_citations(self, text: str, chunks: list[RetrievedChunk]) -> list[Citation]:
        cited_indices = sorted({int(n) for n in CITATION_PATTERN.findall(text)})
        citations = []
        for n in cited_indices:
            if 1 <= n <= len(chunks):
                c = chunks[n - 1]
                citations.append(Citation(index=n, document_id=c.document_id, chunk_id=c.chunk_id, text=c.text))
        return citations
