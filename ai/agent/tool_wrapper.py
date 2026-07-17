"""Safe LangChain tool wrappers for commitment feedback."""

from __future__ import annotations

import logging
from typing import Callable

from langchain_core.tools import StructuredTool

log = logging.getLogger("tramice.tool_wrapper")


def wrap_tool_safe(tool: StructuredTool) -> StructuredTool:
    """Wrap a tool so exceptions become French error strings, never silent fails."""
    original = tool.func

    def _safe(*args, **kwargs):
        try:
            result = original(*args, **kwargs)
            if result is None or (isinstance(result, str) and not result.strip()):
                return "Échec : l'outil n'a rien renvoyé."
            return result
        except Exception as exc:  # noqa: BLE001
            log.warning("Tool %s failed: %s", tool.name, exc)
            return f"Échec ({tool.name}) : {exc}"

    return StructuredTool.from_function(
        func=_safe,
        name=tool.name,
        description=tool.description,
        args_schema=getattr(tool, "args_schema", None),
    )


def wrap_tools_safe(tools: list) -> list:
    return [wrap_tool_safe(t) if isinstance(t, StructuredTool) else t for t in tools]


def filter_tools_for_harness(tools: list, harness: str) -> list:
    """Return tool subset for procedural vs creative harness."""
    light_names = {
        "get_social_norms",
        "list_mondo",
        "get_playtest_stats",
        "get_discord_capabilities",
        "get_guild_metadata",
    }
    if harness == "creative":
        return [t for t in tools if getattr(t, "name", "") in light_names]
    return tools
