"""Agent state schema (spec §3.2).

Extends the prebuilt ReAct ``AgentState`` (``messages`` + ``remaining_steps``)
with Tramice-specific context fields. Extra fields are ``NotRequired`` so the
agent input only needs ``messages``; the others are available to custom nodes
and future stateful workflows.
"""

from __future__ import annotations

from typing import Any, Literal, NotRequired

from langgraph.prebuilt.chat_agent_executor import AgentState as _ReactState


class AgentState(_ReactState):
    user_id: NotRequired[str]
    channel_id: NotRequired[str]
    guild_id: NotRequired[str | None]
    surface: NotRequired[Literal["salon", "dm"]]
    rag_context: NotRequired[list[dict]]
    server_context: NotRequired[dict]
    metadata: NotRequired[dict[str, Any]]
