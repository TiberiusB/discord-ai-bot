# Configuration

Part of the [design documentation](README.md) for the Tramice721 Discord bot. Section numbers are kept from the original single-file specification so that `§n` references elsewhere in the docs stay meaningful.

## 9. Configuration



### 9.1 Environment (`.env`)

```bash
DISCORD_TOKEN=
OLLAMA_HOST=http://127.0.0.1:11434
GUILD_ID=                    # primary lab server
ADMIN_ROLE_IDS=              # comma-separated
DISCORD_LOG_LEVEL=WARNING    # set INFO for first-connect diagnostics
```



### 9.2 `config.yaml`

```yaml
bot:
  name: "Tramice721"
  prefix: "!ai"
  locale_default: fr
  timezone: America/Montreal

llm:
  model: qwen2.5:7b-instruct
  temperature: 0.7
  max_tokens: 2048
  embed_model: nomic-embed-text

channels:
  log_mode: allowlist          # allowlist | denylist | all
  interact_allowlist: []       # bot replies / triggers
  log_allowlist: []            # message logging (may be superset)
  denylist: []
  summary_channel_id: null

features:
  game_simulation: true
  matchmaking: true
  web_fetch: false
  everyone_announcements: false
  tts: true                    # admin /say

governance:
  escalation_threshold: 3      # open signalements before admin DM suggestion

rate_limit:
  per_user_cooldown_sec: 10
  per_channel_cooldown_sec: 5
  max_queue_depth: 20

rag:
  chunk_size: 800
  chunk_overlap: 120
  collections: [docs, history, web]
  web:
    max_depth: 2
    max_pages: 25
    fetch_timeout_sec: 15
    require_allowlist: false   # true = seed domain must match fetch_allowlist
    user_agent: "Tramice721-RAG/1.0"

privacy:
  dm_always_private: true
  confidences_never_shared: true

social_norms_defaults:
  dm_always_private: true
  transaction_details_general: true
  personal_addresses_hidden: true

fetch_allowlist:
  - latramice.net
  - la-tramice.net
```



### 9.3 Default social norms (bootstrapped into `social_norms` table)


| Key                           | Default | Effect                                           |
| ----------------------------- | ------- | ------------------------------------------------ |
| `dm_always_private`           | `true`  | DMs excluded from public summaries and Cosmo     |
| `confidences_never_shared`    | `true`  | `confidences` table never in RAG/history exports |
| `personal_addresses_hidden`   | `true`  | Strip/limit address fields in public profiles    |
| `transaction_details_general` | `true`  | HOP transaction descriptions default to general  |
