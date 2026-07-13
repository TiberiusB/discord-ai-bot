"""Tests for checkpoint cleanup."""

import sqlite3
from pathlib import Path

from storage.checkpoints import forget_user_threads


def test_forget_user_threads_deletes_matching_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "checkpoints.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE checkpoints (thread_id TEXT, checkpoint_ns TEXT, checkpoint_id TEXT)"
    )
    conn.execute(
        "INSERT INTO checkpoints VALUES ('user1-ch1', 'ns', '1'), ('user2-ch1', 'ns', '2')"
    )
    conn.commit()
    conn.close()

    deleted = forget_user_threads(db_path, "user1")
    assert deleted == 1

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT thread_id FROM checkpoints").fetchall()
    conn.close()
    assert rows == [("user2-ch1",)]
