"""Entrypoint: wire configuration, storage, Ollama, agent, and the Discord bot.

Run with::

    python -m bot.main
"""

from __future__ import annotations

import asyncio
import logging
import sys

from ai.ollama_client import OllamaClient
from bot.config import load_settings
from storage.db import build_database
from storage.history import HistoryStore

log = logging.getLogger("tramice")


def configure_logging() -> None:
    """Configure logging. Set ``LOG_JSON=1`` for structured JSON output (§11.2)."""
    import os

    handler = logging.StreamHandler(sys.stdout)
    if os.getenv("LOG_JSON") in {"1", "true", "yes"}:
        from bot.observability import JsonFormatter

        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
        )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]
    logging.getLogger("discord").setLevel(logging.WARNING)


async def run() -> None:
    settings = load_settings()
    if not settings.discord_token:
        log.error(
            "DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in."
        )
        return

    db = build_database(settings)
    history = HistoryStore(db)
    ollama = OllamaClient(
        host=settings.ollama_host,
        model=settings.model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )

    from services.registry import build_services

    services = build_services(settings, db, history)

    # Startup health check (spec §11.3): warn but do not abort if Ollama is down.
    if await ollama.ping():
        log.info("Ollama reachable at %s (model=%s)", settings.ollama_host, settings.model)
    else:
        log.warning(
            "Ollama not reachable at %s. Start it with `ollama serve`.",
            settings.ollama_host,
        )

    responder = build_responder(settings, db, history, ollama, services)

    from bot.discord_client import TramiceBot

    bot = TramiceBot(settings, db, history, ollama, responder, services=services)

    # Let admin /model swaps propagate to the agent responder if it caches a model.
    bot.on_model_changed = getattr(responder, "on_model_changed", lambda _name: None)

    try:
        await bot.start(settings.discord_token)
    finally:
        await bot.close()
        db.close()


def build_responder(settings, db, history, ollama, services=None):
    """Construct the active responder.

    Prefers the stateful LangGraph agent (M2+); falls back to the direct
    single-turn responder if the agent cannot be built (e.g. missing deps).
    Tools are supplied by the agent tools factory (wired in M4).
    """
    try:
        from ai.agent.graph import AgentResponder
        from ai.agent.tools import build_tools_provider
        from mcp_servers.mcp_config import load_mcp_tools

        tools_provider = build_tools_provider(settings, services)
        return AgentResponder(
            settings,
            db,
            history,
            ollama,
            tools_provider=tools_provider,
            mcp_loader=load_mcp_tools,
        )
    except Exception:  # noqa: BLE001
        log.exception("Falling back to DirectResponder (agent unavailable)")
        from ai.responder import DirectResponder

        return DirectResponder(ollama, db)


def main() -> None:
    configure_logging()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("Shutting down.")


if __name__ == "__main__":
    main()
