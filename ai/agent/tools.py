"""LangChain tools exposing services to the agent (spec §6.1).

M2 ships an empty tool set so the react agent runs as a memory-backed chat.
M4 populates ``build_local_tools`` with service-backed tools, and MCP tools are
merged in via :mod:`mcp_servers.mcp_config`.
"""

from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger("tramice.tools")


def build_local_tools(settings, services) -> list:
    """Return LangChain tools wrapping local services. Populated in M4."""
    tools: list = []
    if services is None:
        return tools
    try:
        from ai.agent.service_tools import make_service_tools

        tools.extend(make_service_tools(settings, services))
    except ImportError:
        pass
    return tools


def build_tools_provider(settings, services) -> Callable[[], list]:
    """Return a zero-arg callable yielding the current tool list.

    The agent calls this each time it compiles, so tools added later (e.g. after
    services initialize) are picked up on the next agent (re)build.
    """

    def _provider() -> list:
        return build_local_tools(settings, services)

    return _provider
