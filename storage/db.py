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

-- Post-MVP: deletion traces, member identity --------------------------------
CREATE TABLE IF NOT EXISTS activity_traces (
    user_id         TEXT PRIMARY KEY,
    display_name    TEXT,
    first_activity  TEXT,
    last_activity   TEXT,
    message_count   INTEGER NOT NULL DEFAULT 0,
    forgotten_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS member_aliases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       TEXT NOT NULL,
    name          TEXT NOT NULL,
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL,
    is_current    INTEGER NOT NULL DEFAULT 0,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS identity_links (
    user_id_a     TEXT NOT NULL,
    user_id_b     TEXT NOT NULL,
    linked_by     TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    PRIMARY KEY (user_id_a, user_id_b),
    CHECK (user_id_a < user_id_b)
);

-- Per-user preferences: chosen Ollama chat model (falls back to the global
-- default when absent). Set via /modele, cleared on /forgetme.
CREATE TABLE IF NOT EXISTS user_model_prefs (
    discord_user_id   TEXT PRIMARY KEY,
    model             TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

-- Curated web sources for RAG (admin-managed, shallow same-domain crawl)
CREATE TABLE IF NOT EXISTS web_sources (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    seed_url         TEXT NOT NULL UNIQUE,
    domain           TEXT NOT NULL,
    label            TEXT,
    max_depth        INTEGER NOT NULL DEFAULT 2,
    max_pages        INTEGER NOT NULL DEFAULT 25,
    added_by         TEXT NOT NULL,
    added_at         TEXT NOT NULL,
    last_indexed_at  TEXT,
    last_page_count  INTEGER DEFAULT 0,
    last_chunk_count INTEGER DEFAULT 0,
    last_error       TEXT,
    active           INTEGER NOT NULL DEFAULT 1
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

    # ---- per-user model preference ------------------------------------
    def get_user_model(self, user_id: str) -> str | None:
        """Return the user's chosen chat model, or None to use the default."""
        row = self.query_app_one(
            "SELECT model FROM user_model_prefs WHERE discord_user_id = ?",
            (user_id,),
        )
        return row["model"] if row else None

    def set_user_model(self, user_id: str, model: str) -> None:
        self.execute_app(
            "INSERT INTO user_model_prefs(discord_user_id, model, updated_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(discord_user_id) DO UPDATE SET "
            "model = excluded.model, updated_at = excluded.updated_at",
            (user_id, model, utcnow()),
        )

    def clear_user_model(self, user_id: str) -> int:
        return self.execute_app(
            "DELETE FROM user_model_prefs WHERE discord_user_id = ?",
            (user_id,),
        ).rowcount

    # ---- curated web sources (RAG) ------------------------------------
    def list_web_sources(self, active_only: bool = True) -> list[sqlite3.Row]:
        if active_only:
            return self.query_app(
                "SELECT * FROM web_sources WHERE active = 1 ORDER BY id"
            )
        return self.query_app("SELECT * FROM web_sources ORDER BY id")

    def get_web_source(self, source_id: int) -> sqlite3.Row | None:
        return self.query_app_one(
            "SELECT * FROM web_sources WHERE id = ?",
            (source_id,),
        )

    def get_web_source_by_url(self, seed_url: str) -> sqlite3.Row | None:
        return self.query_app_one(
            "SELECT * FROM web_sources WHERE seed_url = ?",
            (seed_url,),
        )

    def upsert_web_source(
        self,
        *,
        seed_url: str,
        domain: str,
        added_by: str,
        label: str | None = None,
        max_depth: int = 2,
        max_pages: int = 25,
    ) -> int:
        now = utcnow()
        self.execute_app(
            "INSERT INTO web_sources("
            "seed_url, domain, label, max_depth, max_pages, added_by, added_at, active"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, 1) "
            "ON CONFLICT(seed_url) DO UPDATE SET "
            "domain = excluded.domain, "
            "label = COALESCE(excluded.label, web_sources.label), "
            "max_depth = excluded.max_depth, "
            "max_pages = excluded.max_pages, "
            "active = 1",
            (seed_url, domain, label, max_depth, max_pages, added_by, now),
        )
        row = self.get_web_source_by_url(seed_url)
        return int(row["id"]) if row else 0

    def update_web_source_index_status(
        self,
        source_id: int,
        *,
        last_indexed_at: str | None = None,
        last_page_count: int = 0,
        last_chunk_count: int = 0,
        last_error: str | None = None,
    ) -> None:
        self.execute_app(
            "UPDATE web_sources SET "
            "last_indexed_at = ?, last_page_count = ?, last_chunk_count = ?, "
            "last_error = ? WHERE id = ?",
            (last_indexed_at, last_page_count, last_chunk_count, last_error, source_id),
        )

    def delete_web_source(self, source_id: int) -> bool:
        cur = self.execute_app("DELETE FROM web_sources WHERE id = ?", (source_id,))
        return cur.rowcount > 0

    def delete_web_source_by_url(self, seed_url: str) -> bool:
        cur = self.execute_app(
            "DELETE FROM web_sources WHERE seed_url = ?",
            (seed_url,),
        )
        return cur.rowcount > 0

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

    def query_history_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            return self.history.execute(sql, params).fetchone()


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
