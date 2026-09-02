# Data model

Part of the [design documentation](README.md) for the Tramice721 Discord bot. Section numbers are kept from the original single-file specification so that `§n` references elsewhere in the docs stay meaningful.

## 4. Data model

Two SQLite databases plus Chroma.

### 4.1 `history.sqlite` and `app.sqlite`: the DDL `[community-memory]` `[identity]` `[game]` `[governance]`

The schema below is generated from `storage/db.py` by `scripts/dump_schema.py` and checked by `tests/test_schema_doc.py`, so it cannot drift from the code. After changing the DDL, run `python scripts/dump_schema.py` and commit [`schema.sql`](schema.sql).

- `history.sqlite` holds the community memory: the `messages` log with its indexes. **Retention:** soft-delete via `deleted=1` on `/forgetme`; hard-delete is an optional admin job.
- `app.sqlite` holds the domain entities: trammers, volios and identity links; enterprises, quests and entity updates; teams, events and tasks; the weekly game simulation (weeks, missions, placements, recognitions); governance (votes, signalements, tribunals, social norms); and the Échos inbox.

```sql
{{#include schema.sql}}
```

### 4.2 Game invariants `[game]`

**HOP validation rules (enforced in** `services/game.py`**):**

```python
HOP_MIN = 0.0
HOP_MAX_BALANCE = 99_999.99
HOP_DECIMALS = 2
HOP_MAX_INVEST_PER_WEEK = 100.0
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
