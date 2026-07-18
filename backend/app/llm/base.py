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


class LLMClient(Protocol):
    """Every piece of code that needs the model goes through this interface.
    Nothing outside app/llm/fake.py and app/llm/ollama_client.py should import
    an LLM client directly — this is what makes the rest of the codebase
    testable on a machine with no Ollama installed. See docs/TESTING.md."""

    def extract_structured(self, prompt: str, schema: type[T]) -> T:
        """Return a validated instance of `schema` extracted from `prompt`."""
        ...

    def chat_stream(self, messages: list[Message], tools: list[Tool] | None = None) -> Iterator[str]:
        """Stream assistant text for a conversation, optionally with tool use."""
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...
