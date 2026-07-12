# Tramice721 — Discord AI bot

Local-first, model-swappable Discord bot that **is Tramice721** — the social AI
assistant of the *Laboratoire tramiciel n°721* playtest of **La Guilde des
Tramarades**. She simulates the personal *tramice* console: a warm, feminine,
French (Québec) persona that helps trammers connect, learn the game, and run the
weekly HOP cycle.

The bot runs entirely on your machine:

- **[Ollama](https://ollama.com)** for the LLM and embeddings
- **[LangGraph](https://github.com/langchain-ai/langgraph)** react agent with per-thread memory
- **MCP tools** (stdio) for server overview and semantic search
- **Chroma** RAG over project docs and (optionally) chat history
- **SQLite** for domain data, message log, and agent checkpoints
- **APScheduler** for nightly indexing, daily summaries, and the weekly game cycle

Design docs: [`docs/requirements.md`](docs/requirements.md) (what) ·
[`docs/specifications.md`](docs/specifications.md) (how).

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

**Principle:** *L'IA propose, la communauté dispose.* Mutating actions (HOP
placements, events, votes) always require explicit human confirmation.

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

Optional experiments: `mistral`, `gemma2:9b`, `phi3.5`, `deepseek-r1` (weaker at
tool calling on CPU).

### 3. Configure secrets

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

Edit `config.yaml` for channel policy, summary channel, and feature flags (see
[Configuration](#configuration)).

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

## Discord Developer Portal (one-time)

1. [Discord Developer Portal](https://discord.com/developers/applications) →
   **New Application** → **Bot** → copy token → `DISCORD_TOKEN`.
2. Enable intents: **Message Content**, **Server Members**.
3. OAuth2 URL generator: scopes `bot` + `applications.commands`.
4. Bot permissions: Send Messages, Read Message History, Use Slash Commands.
5. Invite the bot to your server; copy the server ID → `GUILD_ID`.

Slash commands sync to `GUILD_ID` on startup (instant). Without `GUILD_ID`,
global sync can take up to an hour.

---

## Talking to Tramice721

| Trigger | Example |
|---------|---------|
| Prefix | `!ai Comment fonctionne le cycle hebdomadaire ?` |
| Mention | `@Tramice721 bonjour` |
| DM | Open a direct message (personal-tramice mode) |
| Slash | `/ask question:Qu'est-ce qu'un HOP ?` |

She does **not** reply to other bots.

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
| `/forgetme` | Delete your stored messages and profile data |

### Admin

| Command | Description |
|---------|-------------|
| `/model` | Swap the Ollama model at runtime |
| `/reindex` | Rebuild the Chroma document index |
| `/norm-set` | Update a social norm |
| `/health` | Report Ollama, SQLite, Chroma, and scheduler status |

Mutations (`/place`, `/event` propose, `/vote` cast) show **✅ Confirmer /
❌ Annuler** buttons before anything is committed.

---

## Configuration

### `config.yaml` (highlights)

```yaml
bot:
  prefix: "!ai"
  timezone: America/Montreal

llm:
  model: qwen2.5:7b-instruct
  embed_model: nomic-embed-text

channels:
  log_mode: allowlist    # allowlist | denylist | all
  allowlist: []          # empty = act everywhere (except denylist)
  summary_channel_id: null   # set for daily summaries + game announcements

features:
  game_simulation: true
  matchmaking: true
  web_fetch: false       # optional MCP fetch for latramice.net

rate_limit:
  per_user_cooldown_sec: 10
  max_queue_depth: 20
```

### Environment variables

| Variable | Purpose |
|----------|---------|
| `DISCORD_TOKEN` | Bot token (required) |
| `GUILD_ID` | Primary server ID (recommended) |
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
| `game_week_open` | Thursday 17:00 | Open investment window; announce budgets |
| `game_week_close` | Sunday 23:59 | Close window; finalize HOP allocations |

Requires `channels.summary_channel_id` for summary and game posts.

---

## Project structure

```
discord-ai-bot/
├── bot/                 # Discord client, router, commands, guardrails delivery
├── services/            # Domain services (identity, game, governance, …)
├── ai/
│   ├── agent/           # LangGraph react agent, tools, state
│   ├── rag/             # Chroma ingest + retrieval
│   ├── persona.py       # System prompt builder
│   └── guardrails.py    # Input/output sanitization
├── mcp_servers/         # FastMCP stdio servers (discord_helper, rag_server)
├── storage/             # SQLite schemas, models, history CRUD
├── scheduler/           # APScheduler job definitions
├── prompts/             # tramice721_system.txt, Ollama Modelfile
├── docs/                # RAG sources (jeu.pdf, requirements, specifications)
├── data/                # Runtime DBs + Chroma (gitignored, created on first run)
├── config.yaml
├── .env.example
├── requirements.txt
├── run.sh
├── Dockerfile
├── docker-compose.yml
└── deploy/tramice721.service
```

Approximate size: **~4,500 lines** of Python application code.

---

## Privacy and data

- Readable salon messages are logged per `channels.log_mode` to power summaries,
  matchmaking, and RAG-over-history.
- **DMs** and **confidences** are treated as private and excluded from public
  summaries and Cosmo views.
- Members can run `/forgetme` to soft-delete their messages and profile rows.
- Post an **AI-logging notice** to your server before going live (GDPR-style).
- Restrict logging with `channels.allowlist` if you do not want all salons indexed.

---

## Deployment

### systemd (Linux)

```bash
# Edit User/WorkingDirectory in deploy/tramice721.service, then:
sudo cp deploy/tramice721.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tramice721
```

### Docker Compose

```bash
# Set DISCORD_TOKEN (and optionally GUILD_ID) in .env
docker compose up --build
```

Ollama runs in a sibling container; mount `./data` and `./docs` for persistence.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Bot exits immediately | `DISCORD_TOKEN` set in `.env`? |
| "Mon moteur de réflexion est indisponible" | `ollama serve` running? Model pulled? |
| RAG returns nothing | Run `python -m ai.rag.ingest`; verify `nomic-embed-text` |
| Slash commands missing | Set `GUILD_ID`; restart bot; wait for guild sync |
| "Je suis un peu débordée" | Queue full or cooldown; wait and retry |
| Slow replies | CPU-only 7B is multi-second; only one LLM request at a time |

Smoke checks:

```bash
python -m storage.db
python -m ai.rag.ingest
python -m bot.main          # needs DISCORD_TOKEN
```

Admin health: `/health` in Discord.

---

## Documentation

| Document | Contents |
|----------|----------|
| [`docs/requirements.md`](docs/requirements.md) | Service catalog, persona, NFRs |
| [`docs/specifications.md`](docs/specifications.md) | Schemas, APIs, acceptance criteria |
| [`docs/jeu.pdf`](docs/jeu.pdf) | Game design (RAG source) |
| [`.cursor/plans/discord_ai_bot_4b8e92eb.plan.md`](.cursor/plans/discord_ai_bot_4b8e92eb.plan.md) | Implementation plan (M0–M6) |

---

## License

Not specified. Add a `LICENSE` file if you intend to distribute this project.
