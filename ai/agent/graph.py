"""Stateful LangGraph react agent (spec §3.2).

``AgentResponder`` wraps ``create_react_agent`` with an async SQLite
checkpointer so each ``thread_id`` (``user_id-channel_id``) keeps its own
conversational memory (IDN-3). Agents are compiled lazily and cached per
(model, surface, norms) so runtime model swaps and norm edits take effect.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging

import aiosqlite
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import create_react_agent

from ai.agent.state import AgentState
from ai.ollama_client import make_chat_model
from ai.persona import build_system_prompt
from ai.responder import OLLAMA_DOWN, load_social_norms
from bot.router import AgentRequest

log = logging.getLogger("tramice.agent")

# ~5 tool calls per turn (spec §3.2): each call is ~2 graph steps, plus slack.
RECURSION_LIMIT = 12


class AgentResponder:
    """Responder backed by the stateful react agent."""

    def __init__(
        self, settings, db, history, ollama, tools_provider=None, mcp_loader=None
    ):
        self.settings = settings
        self.db = db
        self.history = history
        self.ollama = ollama
        # Callable returning the list of local LangChain tools (wired in M3/M4).
        # Default is a no-tool chat agent that still benefits from memory.
        self._tools_provider = tools_provider or (lambda: [])
        # Async callable returning MCP tools (wired in M4); loaded once.
        self._mcp_loader = mcp_loader
        self._mcp_tools: list | None = None

        self._saver: AsyncSqliteSaver | None = None
        self._conn: aiosqlite.Connection | None = None
        self._agents: dict[tuple, object] = {}
        self._init_lock = asyncio.Lock()

    # ---- lifecycle -----------------------------------------------------
    async def _ensure_checkpointer(self) -> AsyncSqliteSaver:
        if self._saver is not None:
            return self._saver
        async with self._init_lock:
            if self._saver is None:
                self._conn = await aiosqlite.connect(
                    str(self.settings.checkpoints_db_path)
                )
                saver = AsyncSqliteSaver(self._conn)
                await saver.setup()
                self._saver = saver
                log.info("Checkpointer ready at %s", self.settings.checkpoints_db_path)
        return self._saver

    def on_model_changed(self, _model: str) -> None:
        """Invalidate cached agents so the new model is used next turn."""
        self._agents.clear()

    def _norms_signature(self, norms: dict) -> str:
        return hashlib.sha1(
            json.dumps(norms, sort_keys=True).encode("utf-8")
        ).hexdigest()[:8]

    async def _ensure_mcp_tools(self) -> list:
        if self._mcp_tools is not None:
            return self._mcp_tools
        if self._mcp_loader is None:
            self._mcp_tools = []
            return self._mcp_tools
        try:
            self._mcp_tools = await self._mcp_loader(self.settings)
        except Exception:  # noqa: BLE001 - MCP optional
            log.exception("MCP tool load failed")
            self._mcp_tools = []
        return self._mcp_tools

    async def _get_agent(self, surface: str, norms: dict):
        model = self.ollama.model
        key = (model, surface, self._norms_signature(norms))
        agent = self._agents.get(key)
        if agent is not None:
            return agent
        saver = await self._ensure_checkpointer()
        mcp_tools = await self._ensure_mcp_tools()
        chat_model = make_chat_model(self.settings, model=model)
        system_prompt = build_system_prompt(surface, norms)
        tools = list(self._tools_provider()) + list(mcp_tools)
        agent = create_react_agent(
            chat_model,
            tools=tools,
            prompt=system_prompt,
            state_schema=AgentState,
            checkpointer=saver,
        )
        self._agents[key] = agent
        return agent

    # ---- responder API -------------------------------------------------
    async def respond(self, req: AgentRequest) -> str:
        if not await self.ollama.ping():
            return OLLAMA_DOWN
        norms = load_social_norms(self.db)
        agent = await self._get_agent(req.surface, norms)
        config = {
            "configurable": {"thread_id": req.thread_id},
            "recursion_limit": RECURSION_LIMIT,
        }
        state_in = {
            "messages": [HumanMessage(content=req.content)],
            "user_id": req.user_id,
            "channel_id": req.channel_id,
            "guild_id": req.guild_id,
            "surface": req.surface,
            "metadata": {"trigger": req.trigger, "command": req.command},
        }
        try:
            result = await agent.ainvoke(state_in, config=config)
        except Exception as exc:  # noqa: BLE001
            log.exception("Agent invocation failed")
            if "connect" in str(exc).lower():
                return OLLAMA_DOWN
            return "Oups, une petite turbulence de mon côté. Peux-tu reformuler ?"
        messages = result.get("messages", [])
        if not messages:
            return "Hmm, je n'ai rien à répondre pour l'instant."
        return getattr(messages[-1], "content", "") or "…"

    async def aclose(self) -> None:
        if self._conn is not None:
            await self._conn.close()
