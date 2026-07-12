"""Responders: turn an :class:`AgentRequest` into a text reply.

``DirectResponder`` (M1) does a single-shot Ollama chat with the persona system
prompt. ``AgentResponder`` (M2) wraps the stateful LangGraph react agent. Both
satisfy the ``Responder`` signature used by :class:`bot.router.Router`.
"""

from __future__ import annotations

import json
import logging

from ai.ollama_client import OllamaClient
from ai.persona import build_system_prompt
from bot.router import AgentRequest
from storage.db import Database

log = logging.getLogger("tramice.responder")

OLLAMA_DOWN = "Mon moteur de réflexion est indisponible. Vérifie qu'Ollama tourne."


def load_social_norms(db: Database) -> dict:
    """Read the current social-norm booleans from ``app.sqlite``."""
    norms: dict = {}
    for row in db.query_app("SELECT key, value FROM social_norms"):
        try:
            norms[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            norms[row["key"]] = row["value"]
    return norms


class DirectResponder:
    """Stateless single-turn responder (M1 baseline)."""

    def __init__(self, ollama: OllamaClient, db: Database):
        self._ollama = ollama
        self._db = db

    async def respond(self, req: AgentRequest) -> str:
        if not await self._ollama.ping():
            return OLLAMA_DOWN
        system = build_system_prompt(req.surface, load_social_norms(self._db))
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": req.content},
        ]
        try:
            return await self._ollama.chat(messages)
        except Exception as exc:  # noqa: BLE001
            log.exception("Ollama chat failed")
            return OLLAMA_DOWN if "connect" in str(exc).lower() else (
                "Oups, une petite turbulence de mon côté. Peux-tu reformuler ?"
            )
