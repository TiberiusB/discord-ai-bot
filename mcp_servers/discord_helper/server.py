"""MCP server: discord_helper (spec §6.2).

Exposes read-only server-activity tools backed by the SQLite message log (not
the live Discord API, to respect rate limits). Runs as a stdio subprocess
launched by the agent via :mod:`mcp_servers.mcp_config`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project importable when launched as a standalone subprocess.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from bot.config import load_settings  # noqa: E402
from storage.db import Database  # noqa: E402
from storage.history import HistoryStore  # noqa: E402

mcp = FastMCP("discord_helper")

_settings = load_settings()
_db = Database(_settings.app_db_path, _settings.history_db_path)
_history = HistoryStore(_db)


@mcp.tool()
def get_server_overview(guild_id: str = "") -> dict:
    """Aperçu du serveur : nombre de messages, salons actifs, participants récents."""
    guild = guild_id or (_settings.guild_id or "")
    total = _db.query_history(
        "SELECT COUNT(*) AS n FROM messages WHERE deleted = 0 AND is_dm = 0"
    )[0]["n"]
    channels = _db.query_history(
        "SELECT channel_id, COUNT(*) AS n FROM messages "
        "WHERE deleted = 0 AND is_dm = 0 GROUP BY channel_id ORDER BY n DESC LIMIT 10"
    )
    people = _db.query_history(
        "SELECT COUNT(DISTINCT user_id) AS n FROM messages WHERE deleted = 0 AND is_dm = 0"
    )[0]["n"]
    return {
        "guild_id": guild,
        "total_messages": total,
        "distinct_participants": people,
        "top_channels": [{"channel_id": c["channel_id"], "messages": c["n"]} for c in channels],
    }


@mcp.tool()
def fetch_channel_history(channel_id: str, limit: int = 50, since_iso: str = "") -> list[dict]:
    """Messages récents d'un salon (depuis le journal local), du plus ancien au plus récent."""
    rows = _history.fetch_history(
        channel_id, limit=min(limit, 200), since_iso=since_iso or None, include_dm=False
    )
    return [
        {
            "user": r["user_name"] or r["user_id"],
            "content": r["content"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@mcp.tool()
def get_guild_metadata() -> dict:
    """Métadonnées du serveur (cache capabilities.json)."""
    from bot.capabilities import load_capabilities_snapshot

    snap = load_capabilities_snapshot(_settings)
    if not snap:
        return {"error": "Aucun snapshot disponible."}
    return {
        "guild_id": snap.get("guild_id"),
        "guild_name": snap.get("guild_name"),
        "member_count": snap.get("member_count"),
        "channel_count": snap.get("channel_count"),
        "roles": snap.get("roles", [])[:20],
        "scanned_at": snap.get("scanned_at"),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
