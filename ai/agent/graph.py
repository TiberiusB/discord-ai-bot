"""Stateful LangGraph react agent with dual harness (procedural vs creative)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time

import aiosqlite
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import create_react_agent

from ai.agent.harness import harness_for_mode, normalize_mode
from ai.agent.state import AgentState
from ai.agent.tool_wrapper import filter_tools_for_harness, wrap_tools_safe
from ai.ollama_client import make_chat_model
from bot.capabilities import build_capabilities_note, capabilities_signature, load_capabilities_snapshot
from ai.persona import build_system_prompt
from ai.responder import OLLAMA_DOWN, load_social_norms, resolve_model
from bot.router import AgentRequest

from bot.observability import log_turn

log = logging.getLogger("tramice.agent")

RECURSION_LIMIT = 12
TOOLS_UNSUPPORTED_MARKER = "does not support tools"
_TOOL_FAIL = re.compile(r"^Échec", re.IGNORECASE)


def _count_tool_calls(messages: list) -> int:
    return sum(
        1
        for msg in messages
        if isinstance(msg, ToolMessage)
        or (isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None))
    )


def _count_tool_errors(messages: list) -> int:
    return sum(
        1
        for msg in messages
        if isinstance(msg, ToolMessage) and _TOOL_FAIL.match(str(msg.content or ""))
    )


def _append_tool_failure_notice(text: str, messages: list) -> str:
    errors = _count_tool_errors(messages)
    if errors == 0:
        return text
    if "échec" in (text or "").lower() or "impossible" in (text or "").lower():
        return text
    return (
        f"{text}\n\n(Je n'ai pas pu exécuter une action technique ({errors} outil(s) "
        f"en échec). Dis-moi si tu veux que je réessaie autrement.)"
    )


class AgentResponder:
    """Responder backed by the stateful react agent."""

    def __init__(
        self, settings, db, history, ollama, tools_provider=None, mcp_loader=None, services=None
    ):
        self.settings = settings
        self.db = db
        self.history = history
        self.ollama = ollama
        self.services = services
        self._tools_provider = tools_provider or (lambda: [])
        self._mcp_loader = mcp_loader
        self._mcp_tools: list | None = None
        self._saver: AsyncSqliteSaver | None = None
        self._conn: aiosqlite.Connection | None = None
        self._agents: dict[tuple, object] = {}
        self._init_lock = asyncio.Lock()
        self._tool_support: dict[str, bool] = {}

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
        return self._saver

    def on_model_changed(self, _model: str) -> None:
        self._agents.clear()

    async def _model_supports_tools(self, model: str) -> bool:
        if model not in self._tool_support:
            self._tool_support[model] = await self.ollama.supports_tools(model)
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
        except Exception:  # noqa: BLE001
            log.exception("MCP tool load failed")
            self._mcp_tools = []
        return self._mcp_tools

    def _capabilities_signature(self) -> str:
        return hashlib.sha1(
            capabilities_signature(self.settings).encode("utf-8")
        ).hexdigest()[:8]

    def _build_procedural_context(self, req: AgentRequest) -> str:
        parts: list[str] = []
        knowledge = getattr(self.services, "knowledge", None) if self.services else None
        if knowledge is not None and req.content:
            try:
                chunks = knowledge.search(req.content, collections=["docs", "web"], k=4)
                if chunks:
                    parts.append("## Sources documentaires")
                    parts.extend(f"[{c.source}] {c.text[:400]}" for c in chunks)
            except Exception:  # noqa: BLE001
                log.exception("Procedural RAG prefetch failed")
        if self.history and req.channel_id:
            try:
                rows = self.history.fetch_history(
                    req.channel_id, limit=8, include_dm=req.surface == "dm"
                )
                if rows:
                    parts.append("## Activité récente du fil")
                    parts.extend(
                        f"{r.get('user_name') or r.get('user_id')}: {r.get('content', '')[:200]}"
                        for r in rows
                    )
            except Exception:  # noqa: BLE001
                log.exception("Procedural history prefetch failed")
        return "\n".join(parts)

    async def _get_agent(
        self,
        surface: str,
        norms: dict,
        model: str,
        with_tools: bool,
        conversation_mode: str,
        harness: str,
    ):
        key = (
            model,
            surface,
            self._norms_signature(norms),
            self._capabilities_signature(),
            with_tools,
            normalize_mode(conversation_mode),
            harness,
        )
        agent = self._agents.get(key)
        if agent is not None:
            return agent
        saver = await self._ensure_checkpointer()
        chat_model = make_chat_model(self.settings, model=model)
        cap_snap = load_capabilities_snapshot(self.settings)
        cap_note = build_capabilities_note(cap_snap)
        system_prompt = build_system_prompt(
            surface,
            norms,
            capabilities_note=cap_note,
            conversation_mode=conversation_mode,
            harness=harness,
        )
        if with_tools:
            mcp_tools = await self._ensure_mcp_tools()
            tools = wrap_tools_safe(
                filter_tools_for_harness(
                    list(self._tools_provider()) + list(mcp_tools),
                    harness,
                )
            )
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
        conversation_mode = self.db.get_channel_mode(req.channel_id)
        harness = harness_for_mode(conversation_mode)
        with_tools = await self._model_supports_tools(model)
        agent = await self._get_agent(
            req.surface, norms, model, with_tools, conversation_mode, harness
        )
        config = {
            "configurable": {"thread_id": req.thread_id},
            "recursion_limit": RECURSION_LIMIT,
        }
        content = req.content
        if harness == "procedural":
            ctx = self._build_procedural_context(req)
            if ctx:
                content = f"{req.content}\n\n---\nContexte récupéré :\n{ctx}"
        state_in = {
            "messages": [HumanMessage(content=content)],
            "user_id": req.user_id,
            "channel_id": req.channel_id,
            "guild_id": req.guild_id,
            "surface": req.surface,
            "metadata": {
                "trigger": req.trigger,
                "command": req.command,
                "mode": conversation_mode,
                "harness": harness,
            },
        }
        try:
            result = await agent.ainvoke(state_in, config=config)
        except Exception as exc:  # noqa: BLE001
            if with_tools and TOOLS_UNSUPPORTED_MARKER in str(exc).lower():
                self._tool_support[model] = False
                agent = await self._get_agent(
                    req.surface, norms, model, False, conversation_mode, harness
                )
                try:
                    result = await agent.ainvoke(state_in, config=config)
                except Exception:  # noqa: BLE001
                    log.exception("No-tools retry failed")
                    return "Oups, une petite turbulence de mon côté. Peux-tu reformuler ?"
            else:
                log.exception("Agent invocation failed")
                if "connect" in str(exc).lower():
                    return OLLAMA_DOWN
                return "Oups, une petite turbulence de mon côté. Peux-tu reformuler ?"
        messages = result.get("messages", [])
        tool_calls = _count_tool_calls(messages)
        tool_errors = _count_tool_errors(messages)
        log_turn(
            user_id=req.user_id,
            channel_id=req.channel_id,
            guild_id=req.guild_id,
            trigger=req.trigger,
            duration_ms=(time.monotonic() - started) * 1000,
            model=model,
            tool_calls=tool_calls,
            status="ok" if tool_errors == 0 else "tool_errors",
        )
        if not messages:
            return "Hmm, je n'ai rien à répondre pour l'instant."
        reply = getattr(messages[-1], "content", "") or "…"
        return _append_tool_failure_notice(reply, messages)

    async def aclose(self) -> None:
        if self._conn is not None:
            await self._conn.close()
