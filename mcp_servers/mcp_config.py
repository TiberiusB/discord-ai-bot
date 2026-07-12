"""MCP client configuration (spec §6, §2.2).

Builds a ``MultiServerMCPClient`` that launches the local stdio MCP servers and
loads their tools into LangChain format for the agent. Failures are non-fatal:
the agent keeps its in-process tools if MCP servers cannot start.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

log = logging.getLogger("tramice.mcp")

_ROOT = Path(__file__).resolve().parents[1]
DISCORD_HELPER = _ROOT / "mcp_servers" / "discord_helper" / "server.py"
RAG_SERVER = _ROOT / "mcp_servers" / "rag_server" / "server.py"


def build_connections(settings) -> dict:
    """Return the MultiServerMCPClient connection map (stdio transport)."""
    python = sys.executable
    connections: dict = {
        "discord_helper": {
            "transport": "stdio",
            "command": python,
            "args": [str(DISCORD_HELPER)],
        },
        "rag_server": {
            "transport": "stdio",
            "command": python,
            "args": [str(RAG_SERVER)],
        },
    }
    # Optional read-only web fetch scoped to the configured allowlist (§6.4).
    if settings.get("features.web_fetch", False):
        connections["fetch"] = {
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp-server-fetch"],
        }
    return connections


async def load_mcp_tools(settings) -> list:
    """Start MCP servers and return their tools as LangChain tools."""
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(build_connections(settings))
        tools = await client.get_tools()
        log.info("Loaded %d MCP tools", len(tools))
        return tools
    except Exception:  # noqa: BLE001 - MCP is optional; degrade gracefully
        log.exception("Failed to load MCP tools; continuing with local tools only")
        return []
