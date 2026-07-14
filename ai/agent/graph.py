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
import time

import aiosqlite
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import create_react_agent

from ai.agent.state import AgentState
from ai.ollama_client import make_chat_model
from bot.capabilities import build_capabilities_note, capabilities_signature, load_capabilities_snapshot
from ai.persona import build_system_prompt
from ai.responder import OLLAMA_DOWN, load_social_norms, resolve_model
from bot.router import AgentRequest

from bot.observability import log_turn

log = logging.getLogger("tramice.agent")

# ~5 tool calls per turn (spec §3.2): each call is ~2 graph steps, plus slack.
RECURSION_LIMIT = 12

# Substring Ollama returns (HTTP 400) when a model lacks tool-calling support.
TOOLS_UNSUPPORTED_MARKER = "does not support tools"


def _count_tool_calls(messages: list) -> int:
    """Count tool invocations in the agent message trace."""
    return sum(
        1
        for msg in messages
        if isinstance(msg, ToolMessage)
        or (isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None))
    )


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
        # Cache of per-model tool-calling support (probed via Ollama `show`,
        # corrected at runtime if inference reports otherwise).
        self._tool_support: dict[str, bool] = {}

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

    async def _model_supports_tools(self, model: str) -> bool:
        """Return (and cache) whether ``model`` can do tool calling."""
        if model not in self._tool_support:
            self._tool_support[model] = await self.ollama.supports_tools(model)
            if not self._tool_support[model]:
                log.info("Model %s has no tool support; using a no-tools agent", model)
        return self._tool_support[model]

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

    def _capabilities_signature(self) -> str:
        return hashlib.sha1(
            capabilities_signature(self.settings).encode("utf-8")
        ).hexdigest()[:8]

    async def _get_agent(self, surface: str, norms: dict, model: str, with_tools: bool):
        key = (
            model,
            surface,
            self._norms_signature(norms),
            self._capabilities_signature(),
            with_tools,
        )
        agent = self._agents.get(key)
        if agent is not None:
            return agent
        saver = await self._ensure_checkpointer()
        chat_model = make_chat_model(self.settings, model=model)
        cap_snap = load_capabilities_snapshot(self.settings)
        cap_note = build_capabilities_note(cap_snap)
        system_prompt = build_system_prompt(surface, norms, capabilities_note=cap_note)
        if with_tools:
            mcp_tools = await self._ensure_mcp_tools()
            tools = list(self._tools_provider()) + list(mcp_tools)
        else:
            tools = []
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
        started = time.monotonic()
        model = resolve_model(self.db, self.ollama, req.user_id)
        if not await self.ollama.ping():
            log_turn(
                user_id=req.user_id,
                channel_id=req.channel_id,
                guild_id=req.guild_id,
                trigger=req.trigger,
                duration_ms=(time.monotonic() - started) * 1000,
                model=model,
                status="ollama_down",
            )
            return OLLAMA_DOWN
        norms = load_social_norms(self.db)
        with_tools = await self._model_supports_tools(model)
        agent = await self._get_agent(req.surface, norms, model, with_tools)
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
            if with_tools and TOOLS_UNSUPPORTED_MARKER in str(exc).lower():
                # The model can't do tool calling after all: remember this,
                # rebuild a no-tools agent, and retry once so the user still
                # gets an answer (with persona + memory, minus tools).
                log.warning(
                    "Model %s rejected tools at runtime; retrying without tools",
                    model,
                )
                self._tool_support[model] = False
                with_tools = False
                agent = await self._get_agent(req.surface, norms, model, False)
                try:
                    result = await agent.ainvoke(state_in, config=config)
                except Exception:  # noqa: BLE001
                    log.exception("No-tools retry failed for model %s", model)
                    log_turn(
                        user_id=req.user_id,
                        channel_id=req.channel_id,
                        guild_id=req.guild_id,
                        trigger=req.trigger,
                        duration_ms=(time.monotonic() - started) * 1000,
                        model=model,
                        status="error",
                    )
                    return "Oups, une petite turbulence de mon côté. Peux-tu reformuler ?"
            else:
                log.exception("Agent invocation failed")
                log_turn(
                    user_id=req.user_id,
                    channel_id=req.channel_id,
                    guild_id=req.guild_id,
                    trigger=req.trigger,
                    duration_ms=(time.monotonic() - started) * 1000,
                    model=model,
                    status="error",
                )
                if "connect" in str(exc).lower():
                    return OLLAMA_DOWN
                return "Oups, une petite turbulence de mon côté. Peux-tu reformuler ?"
        messages = result.get("messages", [])
        tool_calls = _count_tool_calls(messages)
        log_turn(
            user_id=req.user_id,
            channel_id=req.channel_id,
            guild_id=req.guild_id,
            trigger=req.trigger,
            duration_ms=(time.monotonic() - started) * 1000,
            model=model,
            tool_calls=tool_calls,
            status="ok",
        )
        if not messages:
            return "Hmm, je n'ai rien à répondre pour l'instant."
        return getattr(messages[-1], "content", "") or "…"

    async def aclose(self) -> None:
        if self._conn is not None:
            await self._conn.close()
