# Tramice721 — Discord AI bot

## Introduction
### What this project is

**Tramice721** is a local-first Discord bot that **is** the social AI assistant
from *La Guilde des Tramarades* — not a generic chatbot wrapper. She simulates
the personal **tramice** console: a warm, feminine, French (Québec) persona that
helps **trammers** (community members) connect, learn the game, and participate
in the weekly HOP cycle during the *Laboratoire tramiciel n°721* playtest.

The bot runs entirely on your own hardware:

- **Ollama** for chat and embeddings (default: `qwen2.5:7b-instruct`, `nomic-embed-text`;
  trammers can select their own chat model with `/modele`)
- **LangGraph** react agent with per-thread conversational memory
- **Chroma** RAG over project documents and (optionally) indexed salon history
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
3. **The bot** answers game questions from RAG, maintains volios and Échos,
   proposes events and matchmaking, simulates the weekly HOP cycle, and posts
   scheduled summaries and game announcements.
4. **Admins** swap models, reindex documents, adjust social norms, and check
   health via slash commands.


| Doc | Purpose |
|-----|---------|
| [`docs/requirements.md`](docs/requirements.md) | What the bot must do |
| [`docs/specifications.md`](docs/specifications.md) | How it is built |
| [`docs/implementation_status.md`](docs/implementation_status.md) | What is built today |
| [`docs/planning.md`](docs/planning.md) | Gaps and next development phases |
| [`docs/post_mvp.md`](docs/post_mvp.md) | Post-MVP features (capabilities, identity, platform actions) |


**Status:** Application code for milestones M0–M6 is in place; pre-Discord
hardening is done. Live guild testing is the next step — see
[Before you go live](#before-you-go-live).

---

## Architecture

```
Discord (salons · DMs · slash commands)
        │
        ▼
┌───────────────────────────────────────────────────┐
│  Router — rate limits + single-flight LLM queue   │
│  Logger — message log (channel policy)            │
│  Handlers — !ai · @mention · slash                │
└───────────────────────┬───────────────────────────┘
                        ▼
              LangGraph react agent
              (persona + SQLite checkpointer)
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
     Ollama          MCP tools      Service layer
   (LLM + embed)   discord_helper   identity · matchmaking
                   rag_server       coordination · game
                                    ecosystem · governance
                                    knowledge · memory
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
  SQLite                          Chroma
  app · history · checkpoints     docs · history
```

---

## Requirements

| Component | Minimum |
|-----------|---------|
| Python | 3.12 |
| Ollama | installed and running (`ollama serve`) |
| RAM | ~15 GB (CPU-only); 7B models are the practical ceiling |
| GPU | optional; significantly speeds inference |

Default models:

- **Chat / tools:** `qwen2.5:7b-instruct`
- **Embeddings:** `nomic-embed-text`

Target deployment: **single Discord guild**, under **100 members** (no sharding).

---

## Quick start

### 1. Clone and install

```bash
cd discord-ai-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Pull Ollama models

```bash
ollama serve   # if not already running
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

Any additional chat model you pull becomes selectable per-user via `/modele`
(see [Choosing your model](#choosing-your-model-modele)). A tested alternative:

```bash
ollama pull gemma2:9b
```

Other experiments: `mistral`, `phi3.5`, `deepseek-r1` (weaker at tool calling on
CPU).

### 3. Configure secrets and channels

```bash
cp .env.example .env
```

Edit `.env`:

```bash
DISCORD_TOKEN=your_bot_token
GUILD_ID=your_server_id
ADMIN_ROLE_IDS=role_id_1,role_id_2   # optional; guild owner is always admin
OLLAMA_HOST=http://127.0.0.1:11434
```

Edit `config.yaml` — **add at least one channel ID** to `channels.allowlist`
before testing in salons (see [Configuration](#configuration)). DMs work without
an allowlist.

### 4. Initialize data

```bash
python -m storage.db      # creates data/app.sqlite + data/history.sqlite
python -m ai.rag.ingest   # indexes docs/ into Chroma (Ollama must be up)
```

### 5. Run

```bash
./run.sh
# or: python -m bot.main
```

On first run, `data/` is created automatically if missing. Runtime files live
there and are gitignored.

### 6. (Optional) Custom persona model

```bash
ollama create tramice721 -f prompts/tramice721_modelfile
```

Then set `llm.model: tramice721` in `config.yaml`, or swap at runtime with
`/model tramice721`.

---

## Before you go live

Complete this checklist before opening the bot to the wider playtest group. Details
in [`docs/planning.md`](docs/planning.md) Phase 0.

1. [Discord Developer Portal](https://discord.com/developers/applications): create
   app, enable **Message Content** + **Server Members** intents, invite with
   `bot` + `applications.commands` scopes.
2. Set `DISCORD_TOKEN` and `GUILD_ID` in `.env`.
3. Add salon channel IDs to `channels.allowlist` in `config.yaml`.
4. Set `channels.summary_channel_id` if you want daily summaries or game posts.
5. Post the AI-logging notice from [`docs/ai_logging_notice.md`](docs/ai_logging_notice.md).
6. Run `pytest tests/ -q`, then start the bot and smoke-test `/ask`, a DM, and `/health`.

---

## Talking to Tramice721

| Trigger | Example |
|---------|---------|
| Prefix | `!ai Comment fonctionne le cycle hebdomadaire ?` |
| Mention | `@Tramice721 bonjour` |
| DM | Open a direct message (personal-tramice mode) |
| Slash | `/ask question:Qu'est-ce qu'un HOP ?` |

She does **not** reply to other bots. Prefix and mention requests show a cooldown
message when rate-limited; slash commands bypass user cooldown.

---

## Slash commands

### Everyone

| Command | Description |
|---------|-------------|
| `/ask` | Ask Tramice721 a question |
| `/summarize` | Summarize recent activity in the current channel |
| `/volio` | View or add entries to your volio (profile) |
| `/mondo` | Explore the Mondo map (`perso` or `cosmo` view) |
| `/echoes` | View proposed synergies / Échos |
| `/event` | List or propose community events |
| `/mission` | List or publish game Missions |
| `/place` | Place influence HOPs on a Mission (with confirmation) |
| `/vote` | List, open, or cast votes (with confirmation) |
| `/signalement` | File a graduated report (confidential) |
| `/normes` | Show current social norms |
| `/modele` | Choose your personal chat model (dropdown or autocomplete) |
| `/forgetme` | Delete your stored data; retains a minimal activity trace (see [Privacy](#privacy-and-data)) |
| `/identite` | List known display names or link two member identities |
| `/thread` | Create a discussion thread in the current channel |
| `/sondage` | Publish a 24-hour Discord poll (2–4 options) |
| `/son` | List server soundboard sounds (playback not yet automated) |

### Admin

| Command | Description |
|---------|-------------|
| `/model` | Change the **default** Ollama model (dropdown; runtime; not persisted) |
| `/reindex` | Rebuild the Chroma document index |
| `/norm-set` | Update a social norm |
| `/health` | Ollama, SQLite, Chroma, scheduler, gateway, capability scan, error counters |
| `/say` | Send a TTS message in the current channel (`features.tts` must be enabled) |

Mutations (`/place`, `/event` propose, `/vote` cast) show **✅ Confirmer /
❌ Annuler** buttons before anything is committed.

### Choosing your model (`/modele`)

Any trammer can pick which locally-installed Ollama model answers **their own**
conversations, without affecting anyone else:

- `/modele` — show your current model and a **dropdown** of installed chat models.
- `/modele nom:<model>` — switch to a model (e.g. `gemma2:9b`). Must be installed
  in Ollama; the embedding model is filtered out of the choices.
- `/modele nom:defaut` — clear your choice and fall back to the community default.

`/model` (admin) uses the same dropdown pattern for the community default.

The command replies **ephemerally** with a caution note: models differ in
answer quality, speed, and tool-calling reliability (larger models like
`gemma2:9b` are slower on CPU). A change takes effect on your **next message**,
your conversation memory is preserved, and your preference persists across
restarts (stored in `app.sqlite`; cleared by `/forgetme`).

Resolution order per turn: **your `/modele` choice → admin `/model` default →
`llm.model` from `config.yaml`**.

**Tool calling:** some models (e.g. `gemma2:9b`) don't support Ollama's
tool-calling API. The bot detects this (via `ollama show` capabilities) and runs
those models as a **no-tools** agent — full persona and conversation memory, but
without tools like knowledge search, volios, or events. `/modele` warns you when
a chosen model lacks tool support. For the full toolset, pick a tool-capable
model such as `qwen2.5:7b-instruct`.

---

## Configuration

### `config.yaml` (highlights)

```yaml
bot:
  prefix: "!ai"
  timezone: America/Montreal

llm:
  model: qwen2.5:7b-instruct   # community default; per-user override via /modele
  embed_model: nomic-embed-text

channels:
  log_mode: allowlist          # allowlist | denylist | all
  allowlist: []                # REQUIRED for salon access — empty = DMs only
  denylist: []
  summary_channel_id: null     # daily summaries + game announcements

features:
  game_simulation: true
  matchmaking: true
  web_fetch: false             # optional MCP fetch for latramice.net
  tts: true                    # admin /say (requires SEND_TTS_MESSAGES)

governance:
  escalation_threshold: 3      # open signalements before admin DM on /signalement

rate_limit:
  per_user_cooldown_sec: 10
  max_queue_depth: 20
```

In **allowlist** mode, an empty `allowlist` means the bot responds in **DMs only**
until you add channel IDs. This is intentional for a controlled playtest rollout.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `DISCORD_TOKEN` | Bot token (required) |
| `GUILD_ID` | Primary server ID (recommended for instant slash sync) |
| `ADMIN_ROLE_IDS` | Comma-separated admin role IDs |
| `OLLAMA_HOST` | Ollama API URL |
| `LOG_JSON=1` | Structured JSON logs (production) |

---

## Scheduled jobs

All times are **America/Montreal** (configurable in `config.yaml`).

| Job | Schedule | Action |
|-----|----------|--------|
| `index_new_messages` | Daily 02:00 | Embed new salon messages → Chroma `history` |
| `refresh_knowledge_base` | Sunday 03:00 | Re-ingest `docs/` if changed |
| `build_daily_summary` | Daily 08:00 | Post summary to `summary_channel_id` |
| `game_week_open` | Thursday 17:00 | Open investment window; announce budgets; optional Discord scheduled event |
| `game_week_close` | Sunday 23:59 | Close window; finalize HOP allocations |
| `capability_scan` | Daily 04:00 | Refresh `data/capabilities.json` and agent communication strategy |

Requires `channels.summary_channel_id` for summary and game posts. Discord
scheduled events require `MANAGE_EVENTS` on the bot role.

---

## Project structure

```
discord-ai-bot/
├── bot/                 # Discord client, router, commands, capabilities, observability
├── services/            # Domain services (identity, game, governance, …)
├── ai/
│   ├── agent/           # LangGraph react agent, tools, state
│   └── rag/             # Chroma ingest, retrieval, privacy helpers
├── mcp_servers/         # stdio MCP servers (discord_helper, rag_server)
├── storage/             # SQLite schemas, history, checkpoint cleanup
├── scheduler/           # APScheduler job definitions
├── tests/               # pytest unit tests
├── scripts/             # healthcheck.py
├── prompts/             # tramice721_system.txt, Ollama Modelfile
├── docs/                # requirements, specs, status, planning, RAG sources
├── data/                # Runtime DBs + Chroma (gitignored)
├── config.yaml
├── requirements.txt
├── requirements-dev.txt
├── run.sh
├── Dockerfile
├── docker-compose.yml
└── deploy/tramice721.service
```

Approximate size: **~7,100 lines** of Python application code.

---

## Privacy and data

- Readable salon messages are logged per `channels.log_mode` to power summaries,
  matchmaking, and RAG-over-history.
- **DMs** and **confidences** are treated as private and excluded from public
  summaries and Cosmo views.
- `/forgetme` soft-deletes messages and profile rows, removes LangGraph
  checkpoints, and deletes Chroma `history` embeddings for that user. A minimal
  **activity trace** (display name, activity span, message count) is retained in
  `activity_traces` for audit — no message content is kept.
- Display-name changes are tracked in `member_aliases`; use `/identite` to list
  or link identities.
- After repeated `/signalement` reports, admins may receive a **DM suggestion**
  (never an automatic ban).
- Post an **AI-logging notice** before going live —
  [`docs/ai_logging_notice.md`](docs/ai_logging_notice.md).
- Use `channels.allowlist` to limit which salons are logged and where the bot acts.

---

## Deployment

### systemd (Linux)

```bash
# Edit User/WorkingDirectory/EnvironmentFile in deploy/tramice721.service, then:
sudo cp deploy/tramice721.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tramice721
```

The unit loads secrets from `.env` via `EnvironmentFile`.

### Docker Compose

```bash
# Set DISCORD_TOKEN (and optionally GUILD_ID) in .env
docker compose up --build
```

The stack pulls Ollama models on first start (`ollama-init`), mounts `./data` and
`./docs`, and uses `scripts/healthcheck.py` (heartbeat in `data/.health`).

Set `LOG_JSON=1` in production for structured turn and job logging.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Bot exits immediately | `DISCORD_TOKEN` set in `.env`? Check logs for `LoginFailure` or `PrivilegedIntentsRequired` |
| Bot ignores salon messages | `channels.allowlist` includes that channel ID? |
| "Mon moteur de réflexion est indisponible" | `ollama serve` running? Model pulled? |
| RAG returns nothing | Run `python -m ai.rag.ingest`; verify `nomic-embed-text` |
| Slash commands missing | Set `GUILD_ID`; restart bot; check logs for `sync failed` |
| Cooldown / busy message | Queue full or rate limit; wait and retry |
| Slow replies | CPU-only 7B is multi-second; one LLM request at a time |
| Docker unhealthy | Bot running? Check `data/.health` timestamp |
| Discord/gateway issues at connect | Set `DISCORD_LOG_LEVEL=INFO` in `.env`; watch gateway logs |
| Permission errors (403) | Run `/health`; check capability scan + `HTTP code=50013` in logs |

Smoke checks:

```bash
python -m storage.db
python -m ai.rag.ingest
pip install -r requirements-dev.txt && pytest tests/ -q
python -m bot.main          # needs DISCORD_TOKEN
```

Admin health: `/health` in Discord.

---

## Documentation

| Document | Contents |
|----------|----------|
| [`docs/requirements.md`](docs/requirements.md) | Service catalog, persona, NFRs |
| [`docs/specifications.md`](docs/specifications.md) | Schemas, APIs, acceptance criteria |
| [`docs/implementation_status.md`](docs/implementation_status.md) | Built features and known gaps |
| [`docs/planning.md`](docs/planning.md) | Phased roadmap (connect → playtest → hardening) |
| [`docs/post_mvp.md`](docs/post_mvp.md) | Post-MVP features (capabilities, identity, TTS, governance DMs) |
| [`docs/ai_logging_notice.md`](docs/ai_logging_notice.md) | Template notice for server members |
| [`docs/jeu.pdf`](docs/jeu.pdf) | Game design (RAG source) |
| [`.cursor/plans/discord_ai_bot_4b8e92eb.plan.md`](.cursor/plans/discord_ai_bot_4b8e92eb.plan.md) | Original milestone plan (M0–M6) |

---

## License

Not specified. Add a `LICENSE` file if you intend to distribute this project.
