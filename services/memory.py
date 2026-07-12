"""MemoryService (spec §5.8) — community memory: logging, deletion, history.

The daily-summary implementation is added in M5; the method is present here so
the service interface is stable.
"""

from __future__ import annotations

from dataclasses import dataclass

from storage.db import Database
from storage.history import HistoryStore
from storage.models import DiscordMessageSnapshot, Summary


@dataclass
class ForgetResult:
    messages_deleted: int
    volios_deleted: int
    confidences_deleted: int
    echoes_deleted: int
    profile_deleted: bool


class MemoryService:
    def __init__(self, db: Database, history: HistoryStore):
        self.db = db
        self.history = history

    def log_message(self, msg: DiscordMessageSnapshot) -> int:
        return self.history.log_message(msg)

    def fetch_history(self, channel_id: str, limit: int = 50, since: str | None = None):
        return self.history.fetch_history(channel_id, limit=limit, since_iso=since)

    def forget_user(self, user_id: str) -> ForgetResult:
        """Delete a user's stored data (MEM-2, §10.1: only their own data)."""
        messages = self.history.soft_delete_user(user_id)
        volios = self.db.execute_app(
            "DELETE FROM volios WHERE trammer_id = ?", (user_id,)
        ).rowcount
        confidences = self.db.execute_app(
            "DELETE FROM confidences WHERE trammer_id = ?", (user_id,)
        ).rowcount
        echoes = self.db.execute_app(
            "DELETE FROM echoes WHERE trammer_id = ?", (user_id,)
        ).rowcount
        profile = self.db.execute_app(
            "DELETE FROM trammers WHERE discord_user_id = ?", (user_id,)
        ).rowcount
        return ForgetResult(
            messages_deleted=messages,
            volios_deleted=volios,
            confidences_deleted=confidences,
            echoes_deleted=echoes,
            profile_deleted=bool(profile),
        )

    def build_daily_summary(self, guild_id: str) -> Summary:
        """Placeholder until M5 wires GovernanceService summarization."""
        return Summary(
            title="Résumé quotidien",
            body="(Le résumé quotidien sera disponible à l'étape M5.)",
            message_count=0,
        )
