from __future__ import annotations

import hashlib
from collections.abc import Iterator
from typing import cast

from pydantic import BaseModel

from app.llm.base import (  # noqa: F401  (LLMClient documents the interface this satisfies)
    ChatResponse,
    LLMClient,
    Message,
    T,
    Tool,
)


def _dummy_value(annotation):
    origin = getattr(annotation, "__origin__", None)
    if origin in (list, tuple, set):
        return []
    if annotation is str:
        return ""
    if annotation is int:
        return 0
    if annotation is float:
        return 0.0
    if annotation is bool:
        return False
    return None


class FakeLLMClient:
    """Deterministic, network-free LLM client. Backs every unit/integration
    test and CI — no Ollama required to run `pytest`. Register canned
    responses via `register_structured` / `register_chat` keyed by a substring
    of the prompt; anything unmatched falls back to a minimally-valid
    synthesized instance so tests never crash on a missing fixture — they only
    fail on wrong *content*, which is what you actually want to assert on."""

    def __init__(self) -> None:
        self.structured_responses: dict[str, BaseModel] = {}
        self.chat_responses: dict[str, str] = {}
        self.chat_sequences: dict[str, list[ChatResponse]] = {}
        self._sequence_index: dict[str, int] = {}
        self.calls: list[dict] = []

    def register_structured(self, prompt_contains: str, response: BaseModel) -> None:
        self.structured_responses[prompt_contains] = response

    def register_chat(self, prompt_contains: str, response: str) -> None:
        self.chat_responses[prompt_contains] = response

    def register_chat_sequence(self, prompt_contains: str, responses: list[ChatResponse]) -> None:
        """Script a multi-turn tool-use conversation: the Nth call() whose
        message history contains `prompt_contains` returns `responses[N]`.
        Once exhausted, further calls keep returning the last response — used
        to test the RCA agent's tool-calling loop without a real model."""
        self.chat_sequences[prompt_contains] = responses
        self._sequence_index[prompt_contains] = 0

    def extract_structured(self, prompt: str, schema: type[T]) -> T:
        self.calls.append({"op": "extract_structured", "prompt": prompt, "schema": schema.__name__})
        for key, response in self.structured_responses.items():
            if key in prompt:
                # The registry is keyed by prompt substring with a BaseModel
                # value — the caller (a test) is responsible for registering a
                # response of the same schema it asks for; that guarantee
                # can't be expressed statically for a test double, so cast.
                return cast(T, response)
        return schema.model_construct(
            **{name: _dummy_value(f.annotation) for name, f in schema.model_fields.items()}
        )

    def chat_stream(self, messages: list[Message], tools: list[Tool] | None = None) -> Iterator[str]:
        self.calls.append({"op": "chat_stream", "messages": [m.content for m in messages]})
        prompt = messages[-1].content if messages else ""
        for key, response in self.chat_responses.items():
            if key in prompt:
                yield response
                return
        yield f"[fake response to: {prompt[:60]}]"

    def chat(self, messages: list[Message], tools: list[Tool] | None = None) -> ChatResponse:
        self.calls.append({"op": "chat", "messages": [m.content for m in messages]})
        last = messages[-1].content if messages else ""
        combined = "\n".join(m.content for m in messages)

        # Checked against only the *last* message so a targeted single-shot
        # registration (e.g. the RCA agent's forced-conclusion prompt) can
        # override an in-progress `chat_sequences` match without ambiguity.
        for key, response in self.chat_responses.items():
            if key in last:
                return ChatResponse(content=response, tool_calls=[])

        # Checked against the full history so a sequence keyed on the
        # original question keeps matching as tool-result turns accumulate.
        for key, responses in self.chat_sequences.items():
            if key in combined:
                idx = self._sequence_index[key]
                if idx < len(responses) - 1:
                    self._sequence_index[key] += 1
                return responses[idx]

        return ChatResponse(content=f"[fake response to: {last[:60]}]", tool_calls=[])

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append({"op": "embed", "count": len(texts)})
        # Deterministic pseudo-embedding derived from a hash, so identical text
        # always produces the same vector — makes retrieval tests reproducible.
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vectors.append([b / 255.0 for b in digest[:16]])
        return vectors
