"""Thin async wrapper around the local Ollama server.

Supports the direct chat path (M1) and runtime model swapping (ADM-1). The
LangGraph agent (M2+) uses :func:`make_chat_model` to obtain a ``ChatOllama``
bound to the currently selected model.
"""

from __future__ import annotations

import logging

from ollama import AsyncClient

log = logging.getLogger("tramice.ollama")


class OllamaClient:
    def __init__(self, host: str, model: str, temperature: float, max_tokens: int):
        self._host = host
        self._client = AsyncClient(host=host)
        self._model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @property
    def host(self) -> str:
        return self._host

    @property
    def model(self) -> str:
        return self._model

    def set_model(self, model: str) -> None:
        log.info("Swapping Ollama model %s -> %s", self._model, model)
        self._model = model

    async def ping(self) -> bool:
        """Return True if the Ollama server responds to a tags query."""
        try:
            await self._client.list()
            return True
        except Exception as exc:  # noqa: BLE001 - health check must not raise
            log.warning("Ollama ping failed: %s", exc)
            return False

    async def list_models(self) -> list[str]:
        try:
            resp = await self._client.list()
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not list Ollama models: %s", exc)
            return []
        models = getattr(resp, "models", None)
        if models is None and isinstance(resp, dict):
            models = resp.get("models", [])
        names: list[str] = []
        for m in models or []:
            name = getattr(m, "model", None) or getattr(m, "name", None)
            if name is None and isinstance(m, dict):
                name = m.get("model") or m.get("name")
            if name:
                names.append(name)
        return names

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Single-shot chat completion. ``messages`` are OpenAI-style dicts."""
        resp = await self._client.chat(
            model=model or self._model,
            messages=messages,
            options={
                "temperature": self.temperature if temperature is None else temperature,
                "num_predict": self.max_tokens,
            },
        )
        message = getattr(resp, "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if content is not None:
                return content
        if isinstance(resp, dict):
            return resp.get("message", {}).get("content", "")
        return str(resp)


def make_chat_model(settings, model: str | None = None):
    """Build a ``ChatOllama`` for the LangGraph agent (imported lazily)."""
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=model or settings.model,
        base_url=settings.ollama_host,
        temperature=settings.temperature,
        num_predict=settings.max_tokens,
    )
