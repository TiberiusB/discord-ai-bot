"""SQLite connection management + schema bootstrap.

Two databases (spec §4):
- ``history.sqlite`` — community memory (message log).
- ``app.sqlite`` — domain entities (identity, game, governance, ...).

Connections use ``check_same_thread=False`` guarded by a re-entrant lock, since
the async agent may touch the DB from worker threads. Scale is small (playtest),
so synchronous sqlite3 is sufficient.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id      TEXT,
    channel_id    TEXT NOT NULL,
    user_id       TEXT NOT NULL,
    user_name     TEXT,
    is_dm         INTEGER NOT NULL DEFAULT 0,
    content       TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    indexed_at    TEXT,
    deleted       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_messages_channel_time ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_unindexed ON messages(indexed_at) WHERE indexed_at IS NULL;
"""

APP_SCHEMA = """
-- Identity -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trammers (
    discord_user_id   TEXT PRIMARY KEY,
    display_name      TEXT,
    locale            TEXT DEFAULT 'fr',
    sponsor_id        TEXT,
    trust_score       REAL DEFAULT 0.0,
    hop_balance       REAL DEFAULT 0.0 CHECK(hop_balance >= 0.0 AND hop_balance <= 99999.99),
    is_tramicien      INTEGER DEFAULT 0,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    FOREIGN KEY (sponsor_id) REFERENCES trammers(discord_user_id)
);

CREATE TABLE IF NOT EXISTS volios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trammer_id    TEXT NOT NULL,
    kind          TEXT NOT NULL,
    label         TEXT NOT NULL,
    details       TEXT,
    visibility    TEXT DEFAULT 'network',
    active        INTEGER DEFAULT 1,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (trammer_id) REFERENCES trammers(discord_user_id)
);

CREATE TABLE IF NOT EXISTS confidences (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trammer_id    TEXT NOT NULL,
    content       TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (trammer_id) REFERENCES trammers(discord_user_id)
);

-- Entities (enterprises, quests, missions, events, places, ideas) ----------
CREATE TABLE IF NOT EXISTS entities (
    id            TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,
    owner_id      TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    phase         TEXT DEFAULT 'draft',
    transparency  REAL DEFAULT 0.5,
    hop_requested REAL DEFAULT 0.0,
    hop_allocated REAL DEFAULT 0.0,
    location      TEXT,
    metadata      TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    FOREIGN KEY (owner_id) REFERENCES trammers(discord_user_id)
);

CREATE TABLE IF NOT EXISTS entity_updates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id     TEXT NOT NULL,
    author_id     TEXT NOT NULL,
    body          TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);

-- Coordination -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS teams (
    id            TEXT PRIMARY KEY,
    name          TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id       TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    joined_at     TEXT NOT NULL,
    PRIMARY KEY (team_id, trammer_id)
);

CREATE TABLE IF NOT EXISTS events (
    id            TEXT PRIMARY KEY,
    organizer_id  TEXT NOT NULL,
    title         TEXT NOT NULL,
    starts_at     TEXT,
    duration_min  INTEGER,
    location      TEXT,
    min_attendees INTEGER DEFAULT 1,
    max_attendees INTEGER,
    status        TEXT DEFAULT 'proposed',
    metadata      TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_rsvps (
    event_id      TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    status        TEXT NOT NULL,
    PRIMARY KEY (event_id, trammer_id)
);

-- Game simulation ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS game_weeks (
    week_id       TEXT PRIMARY KEY,
    starts_at     TEXT NOT NULL,
    invest_end    TEXT NOT NULL,
    hop_created   REAL DEFAULT 0.0,
    growth_factor REAL DEFAULT 1.20,
    influence_min REAL DEFAULT 5.0,
    influence_max REAL DEFAULT 100.0,
    aum_per_trammer REAL DEFAULT 5.0,
    status        TEXT DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS hop_placements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    week_id       TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    entity_id     TEXT NOT NULL,
    hop_amount    REAL NOT NULL CHECK(hop_amount > 0),
    placed_at     TEXT NOT NULL,
    UNIQUE (week_id, trammer_id, entity_id)
);

CREATE TABLE IF NOT EXISTS hop_recognitions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    week_id       TEXT,
    entity_id     TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    hop_amount    REAL NOT NULL CHECK(hop_amount > 0),
    description   TEXT,
    validated     INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL
);

-- Governance ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS social_norms (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    key           TEXT NOT NULL UNIQUE,
    value         TEXT NOT NULL,
    updated_by    TEXT,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS votes (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT,
    threshold     REAL DEFAULT 0.80,
    created_by    TEXT NOT NULL,
    status        TEXT DEFAULT 'open',
    closes_at     TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vote_ballots (
    vote_id       TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    choice        TEXT NOT NULL,
    cast_at       TEXT NOT NULL,
    PRIMARY KEY (vote_id, trammer_id)
);

CREATE TABLE IF NOT EXISTS signalements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id   TEXT NOT NULL,
    target_id     TEXT,
    level         INTEGER NOT NULL,
    description   TEXT NOT NULL,
    status        TEXT DEFAULT 'open',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tribunals (
    id            TEXT PRIMARY KEY,
    signalement_id INTEGER,
    status        TEXT DEFAULT 'mediation',
    decision      TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tribunal_jurors (
    tribunal_id   TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    selected_at   TEXT NOT NULL,
    PRIMARY KEY (tribunal_id, trammer_id)
);

CREATE TABLE IF NOT EXISTS jurisprudence (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tribunal_id   TEXT NOT NULL,
    summary       TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS echoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trammer_id    TEXT NOT NULL,
    source_id     TEXT,
    match_type    TEXT NOT NULL,
    summary       TEXT NOT NULL,
    read          INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL
);
"""


def utcnow() -> str:
    """ISO-8601 UTC timestamp (spec stores times as ISO strings)."""
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Owns the app + history SQLite connections and exposes helpers."""

    def __init__(self, app_path: Path, history_path: Path):
        app_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.parent.mkdir(parents=True, exist_ok=True)

        self.app = sqlite3.connect(str(app_path), check_same_thread=False)
        self.history = sqlite3.connect(str(history_path), check_same_thread=False)
        for conn in (self.app, self.history):
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
        self._lock = threading.RLock()

    # ---- lifecycle -----------------------------------------------------
    def init_schema(self) -> None:
        with self._lock:
            self.history.executescript(HISTORY_SCHEMA)
            self.app.executescript(APP_SCHEMA)
            self.history.commit()
            self.app.commit()

    def bootstrap_social_norms(self, defaults: dict[str, bool]) -> None:
        """Insert default social norms if the table is empty (GOV-10, §9.3)."""
        with self._lock:
            cur = self.app.execute("SELECT COUNT(*) AS n FROM social_norms")
            if cur.fetchone()["n"] > 0:
                return
            now = utcnow()
            for key, value in defaults.items():
                self.app.execute(
                    "INSERT INTO social_norms(key, value, updated_by, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (key, json.dumps(value), "system", now),
                )
            self.app.commit()

    def close(self) -> None:
        with self._lock:
            self.app.close()
            self.history.close()

    # ---- generic helpers ----------------------------------------------
    def execute_app(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self.app.execute(sql, params)
            self.app.commit()
            return cur

    def query_app(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self.app.execute(sql, params).fetchall()

    def query_app_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            return self.app.execute(sql, params).fetchone()

    def execute_history(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self.history.execute(sql, params)
            self.history.commit()
            return cur

    def query_history(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self.history.execute(sql, params).fetchall()


def build_database(settings) -> Database:
    """Create a :class:`Database`, run migrations, and seed social norms."""
    db = Database(settings.app_db_path, settings.history_db_path)
    db.init_schema()
    db.bootstrap_social_norms(settings.get("social_norms_defaults", {}))
    return db


if __name__ == "__main__":  # `python -m storage.db` bootstraps the databases.
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from bot.config import load_settings

    _settings = load_settings()
    _db = build_database(_settings)
    print(f"Initialized {_settings.app_db_path}")
    print(f"Initialized {_settings.history_db_path}")
    _db.close()
