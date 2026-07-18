from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable | None = field(default=None, repr=False)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResponse:
    """Result of a single non-streaming turn. `tool_calls` is empty when the
    model produced a final answer; non-empty when it wants tools executed
    before it continues — the caller (app/rca/agent.py) drives that loop."""

    content: str
    tool_calls: list[ToolCall]


class LLMClient(Protocol):
    """Every piece of code that needs the model goes through this interface.
    Nothing outside app/llm/fake.py and app/llm/ollama_client.py should import
    an LLM client directly — this is what makes the rest of the codebase
    testable on a machine with no Ollama installed. See docs/TESTING.md."""

    def extract_structured(self, prompt: str, schema: type[T]) -> T:
        """Return a validated instance of `schema` extracted from `prompt`."""
        ...

    def chat_stream(self, messages: list[Message], tools: list[Tool] | None = None) -> Iterator[str]:
        """Stream assistant text for a conversation. Used by the Copilot
        (Phase 2), which doesn't need a tool-use loop."""
        ...

    def chat(self, messages: list[Message], tools: list[Tool] | None = None) -> ChatResponse:
        """Single non-streaming turn that can return tool calls instead of
        final text. Used by the RCA agent (Phase 3) tool-use loop."""
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...
