"""CRUD helpers for the ``messages`` table in ``history.sqlite`` (spec §4.1)."""

from __future__ import annotations

import sqlite3

from storage.db import Database, utcnow
from storage.models import DiscordMessageSnapshot


class HistoryStore:
    def __init__(self, db: Database):
        self.db = db

    def log_message(self, msg: DiscordMessageSnapshot) -> int:
        cur = self.db.execute_history(
            """
            INSERT INTO messages
                (guild_id, channel_id, user_id, user_name, is_dm, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                msg.guild_id,
                msg.channel_id,
                msg.user_id,
                msg.user_name,
                1 if msg.is_dm else 0,
                msg.content,
                msg.created_at or utcnow(),
            ),
        )
        return int(cur.lastrowid)

    def fetch_history(
        self,
        channel_id: str,
        limit: int = 50,
        since_iso: str | None = None,
        include_dm: bool = True,
    ) -> list[sqlite3.Row]:
        sql = "SELECT * FROM messages WHERE channel_id = ? AND deleted = 0"
        params: list = [channel_id]
        if since_iso:
            sql += " AND created_at >= ?"
            params.append(since_iso)
        if not include_dm:
            sql += " AND is_dm = 0"
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self.db.query_history(sql, tuple(params))
        return list(reversed(rows))

    def fetch_channel_between(
        self, channel_id: str, since_iso: str, until_iso: str, include_dm: bool = False
    ) -> list[sqlite3.Row]:
        sql = (
            "SELECT * FROM messages WHERE channel_id = ? AND deleted = 0 "
            "AND created_at >= ? AND created_at <= ?"
        )
        params: list = [channel_id, since_iso, until_iso]
        if not include_dm:
            sql += " AND is_dm = 0"
        sql += " ORDER BY created_at ASC"
        return list(self.db.query_history(sql, tuple(params)))

    def fetch_unindexed(self, limit: int = 500, include_dm: bool = False) -> list[sqlite3.Row]:
        sql = (
            "SELECT * FROM messages WHERE indexed_at IS NULL AND deleted = 0"
        )
        if not include_dm:
            sql += " AND is_dm = 0"
        sql += " ORDER BY created_at ASC LIMIT ?"
        return list(self.db.query_history(sql, (limit,)))

    def mark_indexed(self, message_ids: list[int]) -> None:
        if not message_ids:
            return
        now = utcnow()
        placeholders = ",".join("?" for _ in message_ids)
        self.db.execute_history(
            f"UPDATE messages SET indexed_at = ? WHERE id IN ({placeholders})",
            (now, *message_ids),
        )

    def soft_delete_user(self, user_id: str) -> int:
        cur = self.db.execute_history(
            "UPDATE messages SET deleted = 1, content = '[supprimé]' "
            "WHERE user_id = ? AND deleted = 0",
            (user_id,),
        )
        return cur.rowcount

    def user_activity_stats(self, user_id: str) -> dict | None:
        """Aggregate activity for a user before forget (post-MVP trace)."""
        row = self.db.query_history_one(
            "SELECT MIN(created_at) AS first_activity, MAX(created_at) AS last_activity, "
            "COUNT(*) AS message_count "
            "FROM messages WHERE user_id = ? AND deleted = 0",
            (user_id,),
        )
        if not row or not row["message_count"]:
            return None
        name_row = self.db.query_history_one(
            "SELECT user_name FROM messages WHERE user_id = ? AND deleted = 0 "
            "ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        return {
            "first_activity": row["first_activity"],
            "last_activity": row["last_activity"],
            "message_count": int(row["message_count"]),
            "display_name": name_row["user_name"] if name_row else None,
        }

    def fetch_guild_between(
        self, guild_id: str, since_iso: str, until_iso: str
    ) -> list[sqlite3.Row]:
        return list(
            self.db.query_history(
                "SELECT * FROM messages WHERE guild_id = ? AND is_dm = 0 AND deleted = 0 "
                "AND created_at >= ? AND created_at <= ? ORDER BY created_at ASC",
                (guild_id, since_iso, until_iso),
            )
        )

    def recent_guild_channels(self, guild_id: str) -> list[str]:
        rows = self.db.query_history(
            "SELECT DISTINCT channel_id FROM messages "
            "WHERE guild_id = ? AND is_dm = 0 AND deleted = 0",
            (guild_id,),
        )
        return [r["channel_id"] for r in rows]
