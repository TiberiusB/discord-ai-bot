# Implementation Status — Tramice721 Discord Bot

> Last updated: 17 July 2026  
> Audience: developers joining or continuing work on this repository.

---

## Introduction

### What this project is

**Tramice721** is a local-first Discord bot that **is** the social AI assistant
from *La Guilde des Tramarades* — not a generic chatbot wrapper. She simulates
the personal **tramice** console: a warm, feminine, French (Québec) persona that
helps **trammers** (community members) connect, learn the game, and participate
in the weekly HOP cycle during the *Laboratoire tramiciel n°721* playtest.

The bot runs entirely on your own hardware:

- **Ollama** for chat and embeddings (default: `qwen2.5:7b-instruct`, `nomic-embed-text`;
  per-user chat model selectable via `/modele`)
- **LangGraph** react agent with per-thread conversational memory
- **Chroma** RAG over project documents, admin-curated web sources, and (optionally) indexed salon history
- **SQLite** for domain data, message logs, and agent checkpoints
- **MCP tools** (stdio) for server overview and semantic search

Design principle: ***L'IA propose, la communauté dispose.*** The bot proposes
connections, events, HOP placements, and votes — humans always confirm before
anything mutating is committed.

### What we want to build

A **service-oriented monolith**: one deployable Python process that exposes ten
logical services (identity, matchmaking, coordination, game, ecosystem-mapping,
governance, knowledge, community-memory, platform, persona) through a single
LangGraph agent backed by slash commands, prefix/mention triggers, and scheduled
jobs.

The target is a **playtest-ready community assistant** for a Discord server with
under 100 members — not a production financial ledger, not a graphical Mondo UI,
and not multi-server sync (all explicitly out of scope for v1).

### How we will use it

1. **Operators** deploy the bot on a local machine (venv, systemd, or Docker
   Compose), configure `.env` and `config.yaml`, and invite it to the lab Discord
   server.
2. **Trammers** talk to Tramice721 in allowlisted salons (`!ai`, `@mention`,
   slash commands) or in DMs (personal-tramice mode).
3. **The bot** answers game questions from RAG (local docs + curated web sources),
   maintains volios and Échos, proposes events and matchmaking, simulates the weekly
   HOP cycle, and posts scheduled summaries and game announcements.
4. **Admins** swap the community default model, reindex local docs and/or curated
   web sources (`/reindex`, `/web-source`), adjust social norms, and check health
   via slash commands. Any trammer can also pick their own chat model with `/modele`.

The bot is **live on the lab guild** (*Laboratoire tramiciel n°721*). Operators
should keep the AI-logging notice posted
([`ai_logging_notice.md`](ai_logging_notice.md)) and maintain the allowlist in
`config.yaml` as the playtest expands.

---

## Status at a glance

| Area | Status | Notes |
|------|--------|-------|
| Core milestones M0–M6 | **Done** | Code and acceptance criteria complete |
| Pre-Discord hardening | **Done** | Observability, deployment polish, tests, privacy baseline |
| Live Discord smoke test | **Done** | Connected to lab guild; bot responsive; Ollama + agent reasoning verified (July 2026) |
| Playtest hardening | **In progress** | Phase 1 — widen surface carefully; fix friction from real use |
| Automated test suite | **Minimal** | 38 unit tests; no integration tests against Discord or Ollama |
| Production at scale | **Not targeted** | Single guild, CPU-only, no sharding |

Approximate size: **~8,100 lines** of Python application code (excluding
`venv/`, tests, and docs).

---

## Milestone completion

Source of truth for milestone definitions:
[`specifications.md`](specifications.md) §12.

| Milestone | Focus | Status |
|-----------|-------|--------|
| **M0** | Repo skeleton, config, SQLite schemas | Complete |
| **M1** | Discord client, triggers, persona, router, `/ask`, `/model` | Complete |
| **M2** | Message log, `/forgetme`, LangGraph checkpointer, identity tables | Complete |
| **M3** | Chroma RAG, doc ingest, web ingest, `KnowledgeService`, `/reindex`, `/web-source` | Complete |
| **M4** | MCP servers, community services, `/volio` `/mondo` `/echoes` `/event` `/summarize` `/normes` | Complete |
| **M5** | APScheduler jobs, game simulation, `/mission` `/place` `/vote`, signalement | Complete |
| **M6** | Guardrails, audit log, deployment assets, health checks | Complete |

### Pre-Discord improvement round (July 2026)

A focused pass before first Discord connection added:

- Structured turn and job logging (`duration_ms`, `tool_calls`, job status)
- User-visible cooldown messages for prefix/mention interactions
- Global slash-command error handler
- Graceful router shutdown and agent checkpointer cleanup
- Heartbeat file for Docker/system health probes (`data/.health`)
- Startup config warnings (empty allowlist, missing `GUILD_ID`, etc.)
- **Strict allowlist policy**: empty `allowlist` = DMs only (no salon access)
- Extended `/forgetme`: checkpoints + Chroma `history` embeddings (+ model pref)
- AI-logging notice template, systemd `EnvironmentFile`, Docker healthchecks
- Initial `tests/` suite and GitHub Actions CI
- **Per-user model selection** (`/modele`): tramarades choose their own Ollama chat
  model with caution messaging; stored in `user_model_prefs`, resolved per turn

### Post-MVP round (July 2026)

After M0–M6 and the pre-Discord hardening pass, additional platform and
governance features shipped. Deferred leftovers are tracked in
[`post_mvp.md`](post_mvp.md).

**Activity traces on `/forgetme`:** deletes messages, profile, volios,
confidences, checkpoints, Chroma `history` embeddings, and the per-user model
preference, then keeps a minimal `activity_traces` row (display name, first/last
activity, message count, `forgotten_at`) — no message content.

**Member aliases + `/identite`:** display names recorded on logged messages and
on `on_member_update` / `on_user_update` (`member_aliases`). Slash actions:

| Action | Who | Behaviour |
|--------|-----|-----------|
| `noms` (default) | Self, or admin for any member | List known names (including linked accounts) |
| `lier` | Either member, or an admin | Link two Discord user IDs as one person |

**Capability scanner:** at startup and daily 04:00 (Montreal) writes
`data/capabilities.json`; a French strategy note is injected into the agent
prompt and exposed via `get_discord_capabilities`. Tracks send messages, TTS,
threads, scheduled events, `@everyone`, slow-mode bypass, soundboard, external
emojis, voice. On the lab guild: TTS / threads / events / soundboard list are
available; slow-mode bypass is not (`manage_messages` false).

**Platform actions:**

| Feature | Command / trigger | Gate | Notes |
|---------|-------------------|------|-------|
| Threads | `/thread` | `CREATE_*_THREADS` | Implemented |
| Polls | `/sondage` | Channel send | 24 h Discord poll |
| TTS | `/say` (admin) | `SEND_TTS_MESSAGES` + `features.tts` | Used live |
| Soundboard list | `/son` | `USE_SOUNDBOARD` | List only; no voice playback |
| Scheduled events | `/event` confirm, `game_week_open` | `MANAGE_EVENTS` | Lab guild has permission |

**Governance escalation:** after `/signalement`,
`evaluate_moderation()` checks `governance.escalation_threshold` (default **3**)
and level-3 reports, then DMs guild owner + admin roles with a
suspend/ban/mediation *suggestion*. Never bans or suspends autonomously.

**Ops / UI:** `discord_errors.py` + `safe_channel_send`; expanded `/health`
(gateway, queue, capability scan, error counters); `ModelSelectView` dropdowns
for `/model` and `/modele` (plus autocomplete; `/modele nom:defaut` clears
override). Set `DISCORD_LOG_LEVEL=INFO` when diagnosing gateway issues.

**Tests:** `test_post_mvp.py`, `test_discord_errors.py`.

### Live Discord smoke test (July 2026)

First connection to the lab guild validated core platform and AI paths:

| Check | Result |
|-------|--------|
| Gateway / slash sync | Connected; capability scan writes `data/capabilities.json` for the lab guild |
| Triggers | Bot responsive to salon / slash interactions |
| Ollama + agent | Chat model operational; reasoning verified in conversation |
| Mutations exercised | Audit log includes `place_hops`, `say_tts`, `model_swap` |
| Knowledge ops | `/reindex` and `/web-source add` used successfully against live data |
| Scheduler / health | Heartbeat (`data/.health`) and daily `capability_scan` observed while running |

Allowlist and `summary_channel_id` are configured for the lab server. Broader
playtest flows (daily summary quality, weekly game cycle with many tramarades)
remain Phase 1 work — see [`planning.md`](planning.md).

---

## Architecture (as implemented)

```
Discord (salons · DMs · slash commands)
        │
        ▼
┌───────────────────────────────────────────────────┐
│  TramiceBot (discord_client.py)                   │
│  Router — rate limits + single-flight LLM queue   │
│  Handlers — channel policy, trigger detection     │
│  Commands — slash command registration            │
└───────────────────────┬───────────────────────────┘
                        ▼
              LangGraph react agent (graph.py)
              persona + SQLite checkpointer
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
     Ollama          MCP tools      Service layer
   (LLM + embed)   discord_helper   (registry.py)
                   rag_server
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
  SQLite                          Chroma
  app · history · checkpoints     docs · history · web
        │                               ▲
        │ web_sources registry          │ admin `/web-source`
        └───────────────────────────────┘
        │
        ▼
  APScheduler (jobs.py)
```

Entry point: `python -m bot.main` (or `./run.sh`).

---

## Implemented by layer

### Discord platform (`bot/`)

| Component | File(s) | Implemented |
|-----------|---------|-------------|
| Config loader | `config.py` | `.env` + `config.yaml` merge |
| Discord client | `discord_client.py` | Intents, `on_message`, slash sync, chunking |
| Message router | `router.py` | Single-flight queue, cooldowns, `SubmitResult` |
| Trigger handlers | `handlers.py` | Prefix, mention, DM; allowlist/denylist |
| Slash commands | `commands.py` | Full command set (see README) |
| Confirmation UI | `ui.py` | `ConfirmView` for mutating actions; `ModelSelectView` for `/model` `/modele` |
| Capabilities | `capabilities.py` | Permission scan → `data/capabilities.json`; strategy note + `get_discord_capabilities` |
| Discord actions | `discord_actions.py` | Scheduled events, threads, soundboard listing (`attach_discord_event_id`) |
| Discord errors | `discord_errors.py` | Classified French hints, `safe_channel_send`; use `DISCORD_LOG_LEVEL=INFO` to debug |
| Guardrails delivery | via `ai/guardrails.py` | Input sanitize, output post-process |
| Observability | `observability.py` | JSON logs, audit log, turn/job metrics, heartbeat |
| Startup validation | `startup.py` | Pre-launch config warnings |

**Triggers:** `!ai` prefix, `@mention`, DMs, slash commands. Bot ignores other
bots (PLT-5).

**Slash commands (all registered):**

- Everyone: `/ask`, `/summarize`, `/volio`, `/mondo`, `/echoes`, `/event`,
  `/mission`, `/place`, `/vote`, `/signalement`, `/normes`, `/modele`,
  `/forgetme`, `/identite`, `/thread`, `/sondage`, `/son`
- Admin: `/model`, `/reindex`, `/web-source`, `/norm-set`, `/health`, `/say`

**Model selection:** `/modele` lets each trammer choose a locally-installed chat
model for their own conversations (`ModelSelectView` dropdown and autocomplete;
embedding model filtered out; ephemeral replies with a caution note).
`/modele nom:defaut` clears the personal override. Preference is stored in
`app.sqlite` (`user_model_prefs`) and cleared by `/forgetme`. Admin `/model`
sets the runtime default for everyone else (not persisted). Resolution per turn:
per-user choice → admin default → `llm.model` from `config.yaml`.

Models without tool-calling support (e.g. `gemma2:9b`) are detected via
`ollama show` capabilities and run as a **no-tools** react agent (persona +
memory, no tools); a runtime fallback also rebuilds without tools if inference
returns "does not support tools". `/modele` warns the user in that case.

### AI layer (`ai/`)

| Component | File(s) | Implemented |
|-----------|---------|-------------|
| Ollama client | `ollama_client.py` | Chat (per-call model override), ping, model list/swap |
| Model resolution | `responder.py` (`resolve_model`) | Per-user model → default; used by agent + direct responder |
| Persona | `persona.py` | System prompt from `prompts/tramice721_system.txt`; salon vs DM addendum |
| Direct fallback | `responder.py` | Single-turn responder if agent fails to load |
| LangGraph agent | `agent/graph.py` | React agent, checkpointer, tool-call cap, turn logging |
| Agent tools | `agent/tools.py`, `service_tools.py`, `community_tools.py` | Knowledge search + service wrappers |
| RAG ingest | `rag/ingest.py`, `rag/web_ingest.py` | PDF/Markdown → `docs`; messages → `history`; curated URLs → `web` |
| RAG retrieval | `rag/retriever.py`, `embeddings.py` | Vector search via Ollama embeddings |
| RAG privacy | `rag/privacy.py` | Delete user history embeddings on `/forgetme` |
| Guardrails | `guardrails.py` | Strip `@everyone`/`@here`; feminine fixes; link allowlist |

Optional Ollama Modelfile: `prompts/tramice721_modelfile`.

### Service layer (`services/`)

| Service | File | Implemented |
|---------|------|-------------|
| Identity | `identity.py` | Trammers, volios, confidences, aliases, identity links |
| Memory | `memory.py` | Logging facade; `/forgetme` with `activity_traces` (name, span, count only) + model pref |
| Knowledge | `knowledge.py` | RAG search (docs+web), reindex scopes, web source registry |
| Matchmaking | `matchmaking.py` | Synergies, Échos (propose-only) |
| Coordination | `coordination.py` | Events, RSVPs, teams |
| Ecosystem | `ecosystem.py` | Mondo perso/cosmo listings |
| Governance | `governance.py` | Norms, votes, summaries, signalements; `evaluate_moderation` → admin DM suggestions |
| Game | `game.py` | Weekly cycle, HOP rules, missions, placements |
| Registry | `registry.py` | Wires all services at startup |

Not present as a separate module: `services/platform.py` (logic lives in `bot/`).

### Storage (`storage/`)

| Store | File | Purpose |
|-------|------|---------|
| `app.sqlite` | `db.py` | Trammers, volios, entities, game, governance, aliases, activity traces, model prefs, **web_sources** |
| `history.sqlite` | `history.py` | Message log with soft-delete |
| `checkpoints.sqlite` | LangGraph | Per-thread agent memory |
| Checkpoint cleanup | `checkpoints.py` | Delete threads on `/forgetme` |
| Chroma | `data/chroma/` | `docs`, `history`, and `web` collections |

Schemas match [`specifications.md`](specifications.md) §4.

### MCP servers (`mcp_servers/`)

| Server | Transport | Tools |
|--------|-----------|-------|
| `discord_helper` | stdio | Server overview, channel history from SQLite |
| `rag_server` | stdio | Semantic search over Chroma (`docs`, `web`, `history`, `all`) |
| Optional fetch | stdio (`uvx`) | Gated by `features.web_fetch` (default off) |

Wired via `mcp_config.py` → `MultiServerMCPClient`; failures are non-fatal.

### Scheduler (`scheduler/jobs.py`)

All jobs run in `America/Montreal` (configurable):

| Job | Schedule | Status |
|-----|----------|--------|
| `index_new_messages` | Daily 02:00 | Implemented |
| `refresh_knowledge_base` | Sunday 03:00 | Implemented |
| `refresh_web_sources` | Sunday 03:30 | Implemented (active `web_sources` registry) |
| `build_daily_summary` | Daily 08:00 | Implemented (needs `summary_channel_id`) |
| `game_week_open` | Thursday 17:00 | Implemented |
| `game_week_close` | Sunday 23:59 | Implemented |
| `capability_scan` | Daily 04:00 | Implemented (refreshes `data/capabilities.json`) |

Jobs log duration and outcome via `log_job()`.

### Deployment & ops

| Asset | Status |
|-------|--------|
| `run.sh` | venv bootstrap + run |
| `deploy/tramice721.service` | systemd unit with `EnvironmentFile` |
| `Dockerfile` + `docker-compose.yml` | Ollama sidecar, model init, healthchecks |
| `scripts/healthcheck.py` | Heartbeat probe (`data/.health`) |
| `.github/workflows/ci.yml` | pytest on push/PR |
| `requirements.txt` / `requirements-dev.txt` | Runtime and test deps |

Set `LOG_JSON=1` for structured JSON logs in production.

### Tests (`tests/`)

| Module | Covers |
|--------|--------|
| `test_handlers.py` | Allowlist policy, DM logging |
| `test_router.py` | Cooldown, slash bypass, submit status |
| `test_guardrails.py` | Input sanitize, link stripping |
| `test_startup.py` | Launch config warnings |
| `test_checkpoints.py` | Thread deletion on forget |
| `test_post_mvp.py` | Activity traces, aliases, moderation, capabilities |
| `test_discord_errors.py` | Discord error classification, runtime health |
| `test_web_ingest.py` | URL validation, SSRF guards, domain crawl rules |
| `test_knowledge_web.py` | Web source registry, scoped reindex, search collections |

Run: `pip install -r requirements-dev.txt && PYTHONPATH=. pytest tests/ -q` (38 tests)

---

## Known gaps and partial implementations

These are intentional deferrals, spec items not yet wired to Discord, or areas
needing operator decisions — not blockers for a controlled first playtest.

| Item | Status | Notes |
|------|--------|-------|
| Live Discord connection | **Done** | Lab guild connected; smoke test passed (July 2026) |
| Tribunal admin workflow | Partial | `GovernanceService` jury/tribunal methods exist; no slash/admin UI |
| Governance admin DM suggestions | **Done** | `/signalement` → `evaluate_moderation` → `dm_admins` (post-MVP) |
| Member alias / identity linking | **Done** | Auto-track + `/identite` (post-MVP) |
| Activity trace on `/forgetme` | **Done** | `activity_traces` table (post-MVP) |
| Capability scan + agent strategy | **Done** | `capabilities.json` + daily job (post-MVP) |
| Discord threads / polls / TTS | **Done** | `/thread`, `/sondage`, `/say` (post-MVP) |
| Discord scheduled events | **Done** | On `/event` confirm + `game_week_open`; lab guild has `MANAGE_EVENTS` |
| Soundboard playback | Partial | `/son` lists sounds; voice playback not wired |
| Agent-initiated threads / TTS | Not implemented | Slash commands only; agent has `get_discord_capabilities`, not create-thread/TTS tools |
| Identity tools for the agent | Not implemented | `/identite` works; no LangChain wrapper for link/list yet |
| Proactive DMs to members | Not implemented | PLT-4; only reactive DMs and admin escalation today |
| `@everyone` announcements | Not implemented | Capability tracked in strategy; send path gated (`features.everyone_announcements`) |
| Web fetch MCP (live) | Config only | `features.web_fetch: false`; optional runtime fetch via `uvx mcp-server-fetch` |
| Admin-curated web RAG | **Done** | `/web-source`, Chroma `web` collection, `refresh_web_sources` job |
| Output data-classification | Partial | Link allowlist + feminine fixes; no requester/owner checks on private data |
| Tool result size cap (8 KB) | Not implemented | Spec §10.3 |
| Multi-server / sharding | Out of scope | Single guild playtest |
| `LICENSE` file | Missing | README notes this |
| Integration / E2E tests | Missing | No automated Discord or Ollama integration tests |

---

## Operator checklist (live lab)

Initial connect checklist is **complete** for the lab guild. Ongoing ops:

1. Keep `ollama serve` and the bot process running (`./run.sh`, systemd, or Docker).
2. Maintain `channels.allowlist` as new salons are opened to the bot.
3. Keep the AI-logging notice visible ([`ai_logging_notice.md`](ai_logging_notice.md)).
4. Before releases: `PYTHONPATH=. pytest tests/ -q`, then smoke `/ask` + `/health`.
5. Use `/web-source` / `/reindex` when curated knowledge changes.
6. Watch `/health` (gateway, queue, capability scan, job/event errors) after deploys.

---

## Documentation map

| Document | Role |
|----------|------|
| [`implementation_status.md`](implementation_status.md) | What is built today (this document) |
| [`planning.md`](planning.md) | Gaps and phased future development |
| [`requirements.md`](requirements.md) | What the bot must do (service tags, NFRs) |
| [`specifications.md`](specifications.md) | How it is built (schemas, APIs, acceptance criteria) |
| [`post_mvp.md`](post_mvp.md) | Post-MVP wishlist outcome + deferred leftovers only |
| [`ai_logging_notice.md`](ai_logging_notice.md) | Template notice for server members |
| [`README.md`](../README.md) | Quick start, commands, deployment |
| [`jeu.pdf`](jeu.pdf) | Game design (RAG source) |

---

## Suggested next work

Phase 0 (connect + smoke) is done. See [`planning.md`](planning.md) for
**Phase 1 — playtest hardening** and later phases. This document tracks
**current state**; the planning doc tracks **what to build next**.

For questions about design intent, start with `requirements.md` §1–3 (context and
persona). For “is feature X built?”, check the service file and `bot/commands.py`
registration, then this document’s gaps table.
