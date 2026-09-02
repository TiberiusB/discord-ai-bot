# Data model

Part of the [design documentation](README.md) for the Tramice721 Discord bot. Section numbers are kept from the original single-file specification so that `§n` references elsewhere in the docs stay meaningful.

## 4. Data model

Two SQLite databases plus Chroma.

### 4.1 `history.sqlite` — community memory `[community-memory]`

```sql
CREATE TABLE messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id      TEXT,
    channel_id    TEXT NOT NULL,
    user_id       TEXT NOT NULL,
    user_name     TEXT,
    is_dm         INTEGER NOT NULL DEFAULT 0,
    content       TEXT NOT NULL,
    created_at    TEXT NOT NULL,          -- ISO-8601 UTC
    indexed_at    TEXT,                   -- NULL until embedded
    deleted       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_messages_channel_time ON messages(channel_id, created_at);
CREATE INDEX idx_messages_user ON messages(user_id);
CREATE INDEX idx_messages_unindexed ON messages(indexed_at) WHERE indexed_at IS NULL;
```

**Retention:** soft-delete via `deleted=1` on `/forgetme`; hard-delete optional admin job.

### 4.2 `app.sqlite` — domain entities



#### Trammers & identity `[identity]`

```sql
CREATE TABLE trammers (
    discord_user_id   TEXT PRIMARY KEY,
    display_name      TEXT,
    locale            TEXT DEFAULT 'fr',
    sponsor_id        TEXT,               -- parrainage
    trust_score       REAL DEFAULT 0.0,   -- 0..1 best-effort
    hop_balance       REAL DEFAULT 0.0,   -- simulated; CHECK 0..99999.99
    is_tramicien      INTEGER DEFAULT 0,
    profile_json      TEXT,               -- optional structured profile fields
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    FOREIGN KEY (sponsor_id) REFERENCES trammers(discord_user_id)
);

CREATE TABLE volios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trammer_id    TEXT NOT NULL,
    kind          TEXT NOT NULL,          -- search|interest|talent|offer|request|placement
    label         TEXT NOT NULL,
    details       TEXT,
    visibility    TEXT DEFAULT 'network', -- private|network|public
    active        INTEGER DEFAULT 1,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (trammer_id) REFERENCES trammers(discord_user_id)
);

CREATE TABLE confidences (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trammer_id    TEXT NOT NULL,
    content       TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (trammer_id) REFERENCES trammers(discord_user_id)
);
-- Never included in summaries, matchmaking, or public profiles (IDN-6, MEM-3)
```



#### Enterprises & quests `[identity]` `[ecosystem-mapping]` `[game]`

```sql
CREATE TABLE entities (
    id            TEXT PRIMARY KEY,       -- UUID
    kind          TEXT NOT NULL,          -- enterprise|quest|mission|event|place|idea
    owner_id      TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    phase         TEXT DEFAULT 'draft',   -- draft|active|funded|completed|archived
    transparency  REAL DEFAULT 0.5,       -- 0..1; higher ranks first (ECO-5)
    hop_requested REAL DEFAULT 0.0,
    hop_allocated REAL DEFAULT 0.0,
    location      TEXT,
    metadata      TEXT,                   -- JSON: skills, needs, coords, etc.
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    FOREIGN KEY (owner_id) REFERENCES trammers(discord_user_id)
);

CREATE TABLE entity_updates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id     TEXT NOT NULL,
    author_id     TEXT NOT NULL,
    body          TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);
```



#### Teams & coordination `[coordination]`

```sql
CREATE TABLE teams (
    id            TEXT PRIMARY KEY,
    name          TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE team_members (
    team_id       TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    joined_at     TEXT NOT NULL,
    PRIMARY KEY (team_id, trammer_id)
);

CREATE TABLE events (
    id            TEXT PRIMARY KEY,
    organizer_id  TEXT NOT NULL,
    title         TEXT NOT NULL,
    starts_at     TEXT,
    duration_min  INTEGER,
    location      TEXT,
    min_attendees INTEGER DEFAULT 1,
    max_attendees INTEGER,
    status        TEXT DEFAULT 'proposed', -- proposed|confirmed|cancelled|done
    metadata      TEXT,                   -- JSON: entity links, tribunal ref, etc.
    created_at    TEXT NOT NULL
);

CREATE TABLE event_rsvps (
    event_id      TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    status        TEXT NOT NULL,          -- invited|accepted|declined
    PRIMARY KEY (event_id, trammer_id)
);
```



#### Game simulation `[game]`

```sql
CREATE TABLE game_weeks (
    week_id       TEXT PRIMARY KEY,       -- ISO year-week, e.g. 2026-W28
    starts_at     TEXT NOT NULL,          -- Thursday 17:00 local
    invest_end    TEXT NOT NULL,          -- Sunday 23:59:59 local
    hop_created   REAL DEFAULT 0.0,       -- total HOPs recognized prior week
    growth_factor REAL DEFAULT 1.20,
    influence_min REAL DEFAULT 5.0,
    influence_max REAL DEFAULT 100.0,
    aum_per_trammer REAL DEFAULT 5.0,
    status        TEXT DEFAULT 'open'     -- open|investing|closed
);

CREATE TABLE hop_placements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    week_id       TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    entity_id     TEXT NOT NULL,
    hop_amount    REAL NOT NULL CHECK(hop_amount > 0),
    placed_at     TEXT NOT NULL,
    UNIQUE (week_id, trammer_id, entity_id)
);

CREATE TABLE hop_recognitions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    week_id       TEXT,
    entity_id     TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    hop_amount    REAL NOT NULL CHECK(hop_amount > 0),
    description   TEXT,
    validated     INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL
);
```

**HOP validation rules (enforced in** `services/game.py`**):**

```python
HOP_MIN = 0.0
HOP_MAX_BALANCE = 99_999.99
HOP_DECIMALS = 2
HOP_MAX_INVEST_PER_WEEK = 100.0
```



#### Governance `[governance]`

```sql
CREATE TABLE social_norms (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    key           TEXT NOT NULL UNIQUE,   -- e.g. dm_always_private
    value         TEXT NOT NULL,          -- JSON
    updated_by    TEXT,
    updated_at    TEXT NOT NULL
);

CREATE TABLE votes (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT,
    threshold     REAL DEFAULT 0.80,
    created_by    TEXT NOT NULL,
    status        TEXT DEFAULT 'open',    -- open|passed|failed|cancelled
    closes_at     TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE vote_ballots (
    vote_id       TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    choice        TEXT NOT NULL,          -- yes|no|abstain
    cast_at       TEXT NOT NULL,
    PRIMARY KEY (vote_id, trammer_id)
);

CREATE TABLE signalements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id   TEXT NOT NULL,
    target_id     TEXT,
    level         INTEGER NOT NULL,       -- 1=discomfort, 2=breach, 3=danger
    description   TEXT NOT NULL,
    status        TEXT DEFAULT 'open',
    created_at    TEXT NOT NULL
);

CREATE TABLE tribunals (
    id            TEXT PRIMARY KEY,
    signalement_id INTEGER,
    status        TEXT DEFAULT 'mediation', -- mediation|jury|decided|closed
    decision      TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE tribunal_jurors (
    tribunal_id   TEXT NOT NULL,
    trammer_id    TEXT NOT NULL,
    selected_at   TEXT NOT NULL,
    PRIMARY KEY (tribunal_id, trammer_id)
);

CREATE TABLE jurisprudence (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tribunal_id   TEXT NOT NULL,
    summary       TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE echoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trammer_id    TEXT NOT NULL,          -- recipient
    source_id     TEXT,                   -- trammer or entity
    match_type    TEXT NOT NULL,          -- wish_offer|skill_need|synergy
    summary       TEXT NOT NULL,
    read          INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL
);

-- Post-MVP: activity trace, aliases, per-user model preference
CREATE TABLE activity_traces (
    user_id         TEXT PRIMARY KEY,
    display_name    TEXT,
    first_activity  TEXT,
    last_activity   TEXT,
    message_count   INTEGER NOT NULL DEFAULT 0,
    forgotten_at    TEXT NOT NULL
);

CREATE TABLE member_aliases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       TEXT NOT NULL,
    name          TEXT NOT NULL,
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL,
    is_current    INTEGER NOT NULL DEFAULT 0,
    UNIQUE (user_id, name)
);

CREATE TABLE identity_links (
    user_id_a     TEXT NOT NULL,
    user_id_b     TEXT NOT NULL,
    linked_by     TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    PRIMARY KEY (user_id_a, user_id_b),
    CHECK (user_id_a < user_id_b)
);

CREATE TABLE user_model_prefs (
    discord_user_id   TEXT PRIMARY KEY,
    model             TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

-- Per-channel conversation mode (/mode) and shared todos (/todo)
CREATE TABLE channel_modes (
    channel_id    TEXT PRIMARY KEY,
    mode          TEXT NOT NULL DEFAULT 'listen',
    updated_at    TEXT NOT NULL
);

CREATE TABLE channel_todos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id    TEXT NOT NULL,
    body          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'todo',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

-- Curated web sources (admin `/web-source`; shallow same-domain crawl → Chroma `web`)
CREATE TABLE web_sources (
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
```



### 4.3 `checkpoints.sqlite`

Managed by `langgraph-checkpoint-sqlite`; no manual schema in spec.

### 4.4 Chroma collections `[knowledge]` `[community-memory]`


| Collection | Source | Chunk strategy |
| ---------- | ------ | -------------- |
| `docs` | `docs/**/*.pdf`, `docs/**/*.md`, `docs/**/*.txt` (recursive) | 800 tokens, 120 overlap; metadata: `source`, `page` |
| `history` | `messages` where `deleted=0` and policy allows | 400 tokens; metadata: `channel_id`, `user_id`, `created_at` |
| `web` | Admin seed URLs (`web_sources` registry) | Same as `docs`; metadata: `seed_url`, `source_url`, `title`, `fetched_at`, `depth` |

**Web ingest (`ai/rag/web_ingest.py`):** BFS crawl on the **same registrable domain** as the seed URL, up to `rag.web.max_depth` / `max_pages` (per-source overrides via `/web-source add`). HTML only (no JS rendering). SSRF guards block private/localhost targets. Registry in `app.sqlite`; vectors in Chroma `web`. Delete/reindex a source = drop chunks where `seed_url` matches, then re-crawl.
