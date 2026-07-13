"""LangGraph checkpoint cleanup for privacy (MEM-2)."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def forget_user_threads(checkpoints_db_path: Path, user_id: str) -> int:
    """Delete conversational memory for all threads owned by ``user_id``.

    Thread IDs follow ``{user_id}-{channel_id}`` (spec §3.2).
    """
    if not checkpoints_db_path.exists():
        return 0
    prefix = f"{user_id}-"
    deleted = 0
    conn = sqlite3.connect(str(checkpoints_db_path))
    try:
        for table in ("checkpoints", "writes"):
            try:
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE thread_id LIKE ?",
                    (prefix + "%",),
                )
                deleted += cur.rowcount
            except sqlite3.OperationalError:
                continue
        conn.commit()
    finally:
        conn.close()
    return deleted
