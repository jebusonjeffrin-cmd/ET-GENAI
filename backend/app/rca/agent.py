from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.llm.base import LLMClient, Message
from app.rca.tools import RCATools

SYSTEM_PROMPT = """You are Inspiron's Root Cause Analysis agent. An engineer will describe
an equipment failure or incident. Before drafting a root-cause chain, gather evidence using
the available tools — equipment history, work orders, and similar past incidents. Do not
guess at a root cause until you have called at least one tool. When you have enough evidence,
respond with your final root-cause chain as plain text (no more tool calls) — walk through
the causal chain step by step (symptom -> immediate cause -> underlying cause), citing the
specific evidence (document IDs, work order findings) that supports each step."""

FORCE_CONCLUSION_PROMPT = (
    "You've gathered enough evidence. Summarize your root-cause findings now as plain text — "
    "no more tool calls."
)


@dataclass
class EvidenceRef:
    tool: str
    arguments: dict
    result_summary: str


@dataclass
class RCAResult:
    root_cause_chain: str
    evidence: list[EvidenceRef] = field(default_factory=list)


def _summarize(result: object, limit: int = 500) -> str:
    text = json.dumps(result, default=str)
    return text if len(text) <= limit else text[:limit] + "…"


class RCAAgent:
    """Phase 3 core: a tool-use loop that gathers its own evidence before
    drafting a root-cause chain, rather than answering from a single fixed
    retrieval pass. Fully testable with FakeLLMClient's scripted
    `register_chat_sequence` — no Ollama required. See docs/TESTING.md."""

    def __init__(self, llm: LLMClient, tools: RCATools, max_iterations: int = 5) -> None:
        self.llm = llm
        self.tools = tools
        self.tool_defs = tools.as_tool_definitions()
        self.handlers = {t.name: t.handler for t in self.tool_defs if t.handler is not None}
        self.max_iterations = max_iterations

    def investigate(self, incident_description: str) -> RCAResult:
        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=incident_description),
        ]
        evidence: list[EvidenceRef] = []

        for _ in range(self.max_iterations):
            response = self.llm.chat(messages, tools=self.tool_defs)
            if not response.tool_calls:
                return RCAResult(root_cause_chain=response.content, evidence=evidence)

            messages.append(Message(role="assistant", content=response.content))
            for call in response.tool_calls:
                handler = self.handlers.get(call.name)
                result = handler(**call.arguments) if handler else {"error": f"unknown tool {call.name}"}
                evidence.append(EvidenceRef(tool=call.name, arguments=call.arguments, result_summary=_summarize(result)))
                messages.append(Message(role="tool", content=_summarize(result, limit=4000)))

        messages.append(Message(role="user", content=FORCE_CONCLUSION_PROMPT))
        final = self.llm.chat(messages, tools=None)
        return RCAResult(root_cause_chain=final.content, evidence=evidence)
