# Security, privacy, guardrails and observability

Part of the [design documentation](README.md) for the Tramice721 Discord bot. Section numbers are kept from the original single-file specification so that `§n` references elsewhere in the docs stay meaningful.

## 10. Security, privacy & guardrails



### 10.1 Access control


| Action            | Check                                                 |
| ----------------- | ----------------------------------------------------- |
| Admin commands    | `user` has role in `ADMIN_ROLE_IDS` or is guild owner |
| `/web-source add` | admin only; SSRF validation on seed URL                |
| Channel logging   | `log_mode` + allow/deny lists                         |
| Tool mutations    | confirmation UI + audit row in SQLite                 |
| `/forgetme`       | only requesting user's data                           |




### 10.2 Data classification


| Class     | Examples                      | Storage               | RAG | Summaries  | Profiles     |
| --------- | ----------------------------- | --------------------- | --- | ---------- | ------------ |
| `public`  | Mondo entities, public volios | app.sqlite            | yes | yes        | yes          |
| `network` | volio network visibility      | app.sqlite            | yes | anonymized | members only |
| `private` | DMs, confidences              | history + confidences | no  | no         | owner only   |
| `admin`   | social norm config            | app.sqlite            | no  | no         | admin only   |




### 10.3 Input/output sanitization (M6)

- Strip `@everyone` / `@here` from user input to agent.
- Web crawl (`/web-source add`): http(s) only; DNS resolved to public IPs; optional `rag.web.require_allowlist`.
- Max tool-result size 8 KB per call (truncate with pointer).
- Block output of other users' `private` data unless requester is owner or admin.



### 10.4 Audit log (M6)

Append-only `audit.log` JSON lines: `{ts, user_id, action, tool, args_hash, result}`.


## 11. Error handling & observability



### 11.1 User-facing errors (French)


| Condition         | Message                                                                          |
| ----------------- | -------------------------------------------------------------------------------- |
| Queue full        | "Je suis un peu débordée en ce moment — réessaie dans un instant."               |
| Ollama down       | "Mon moteur de réflexion est indisponible. Vérifie qu'Ollama tourne."            |
| RAG miss          | "Je n'ai pas trouvé de source fiable — voici ce que je peux dire avec prudence…" |
| Permission denied | "Je n'ai pas la permission pour cette action."                                   |




### 11.2 Logging

Structured JSON to stdout (M6): `level`, `event`, `guild_id`, `channel_id`,
`user_id`, `duration_ms`, `model`, `tool_calls`.

### 11.3 Health checks

- On startup: ping Ollama `/api/tags`, verify SQLite writable, Chroma reachable;
  run capability scan when `GUILD_ID` is set.
- `/health` admin slash: Ollama, SQLite, Chroma, scheduler jobs, gateway
  latency, router queue, last capability scan, event/job error counters.
