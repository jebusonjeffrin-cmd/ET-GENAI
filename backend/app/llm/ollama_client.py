from __future__ import annotations

import json
from collections.abc import Iterator

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.llm.base import Message, T, Tool


class OllamaExtractionError(RuntimeError):
    """Raised when the model could not produce schema-valid JSON after retries."""


class OllamaLLMClient:
    """Real LLMClient adapter — talks to an Ollama instance over HTTP.

    Points at OLLAMA_HOST: set it to the other laptop's LAN address while
    developing here if it's reachable, or leave it as the default
    localhost:11434 for when this code actually runs on that laptop. Nothing
    else in the codebase changes either way — this class is the only place
    that matters.

    Default model is a 4B-parameter model (`gemma3:4b`) to match the hardware
    already set up. If the laptop has a different model pulled, override via
    OLLAMA_MODEL — no code change needed.
    """

    def __init__(self, host: str | None = None, model: str | None = None, embed_model: str | None = None) -> None:
        settings = get_settings()
        self.host = (host or settings.ollama_host).rstrip("/")
        self.model = model or settings.ollama_model
        self.embed_model = embed_model or settings.ollama_embed_model
        self._client = httpx.Client(base_url=self.host, timeout=120.0)

    def extract_structured(self, prompt: str, schema: type[T], max_retries: int = 2) -> T:
        schema_json = json.dumps(schema.model_json_schema())
        system = (
            "You extract structured data and reply with ONLY valid JSON matching this "
            f"JSON Schema, no commentary, no markdown fences:\n{schema_json}"
        )
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            correction = (
                "" if attempt == 0
                else f"\n\nYour previous reply failed validation: {last_error}. Reply with ONLY corrected JSON."
            )
            response = self._client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt + correction},
                    ],
                    "format": "json",
                    "stream": False,
                },
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]
            try:
                return schema.model_validate_json(content)
            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
        raise OllamaExtractionError(
            f"Model failed to produce valid {schema.__name__} after {max_retries + 1} attempts: {last_error}"
        )

    def chat_stream(self, messages: list[Message], tools: list[Tool] | None = None) -> Iterator[str]:
        payload: dict = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
                }
                for t in tools
            ]
        with self._client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    yield piece
                if chunk.get("done"):
                    break

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            response = self._client.post("/api/embed", json={"model": self.embed_model, "input": text})
            response.raise_for_status()
            vectors.append(response.json()["embeddings"][0])
        return vectors
