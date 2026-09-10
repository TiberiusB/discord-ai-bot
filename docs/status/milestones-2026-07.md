# Milestones 2026-07: acceptance criteria and post-MVP additions

Historical record moved out of the specification on 2026-09-02. What is built today is in [`implementation_status.md`](implementation_status.md); the current slice is [`../requirements/reliability.md`](../requirements/reliability.md).

## 12. Milestone acceptance criteria



### M0 — Foundation

- [x] Repo structure matches [§2.4](../design/architecture.md)
- [x] `config.yaml` + `.env.example` load without error
- [x] `storage/db.py` creates `app.sqlite` + `history.sqlite` schemas



### M1 — Working bot `[platform]` `[persona]`

- [x] Bot connects to Discord; responds to `!ai`, `@mention`, `/ask`
- [x] Direct Ollama call with persona system prompt
- [x] `/model` swaps model at runtime
- [x] Does not reply to other bots



### M2 — Persistence `[community-memory]` `[identity]`

- [x] All readable messages logged per channel policy
- [x] `/forgetme` soft-deletes user messages + profile rows
- [x] LangGraph checkpointer restores multi-turn DM context



### M3 — RAG `[knowledge]`

- [x] `docs/game/jeu.pdf` + `requirements/` ingested into Chroma
- [x] `/ask` about HOP / weekly cycle returns grounded answer with source hint
- [x] `/reindex` rebuilds index (scoped: docs, web, or all)
- [x] Admin-curated web RAG: `/web-source`, Chroma `web`, `refresh_web_sources`



### M4 — MCP & services

- [x] `discord_helper` + `rag_server` wired via MultiServerMCPClient
- [x] `/volio`, `/mondo`, `/echoes`, `/summarize` functional
- [x] Matchmaking proposes connections; no auto-DM
- [x] Social norms readable via `/norms`



### M5 — Scheduling & game `[game]` `[governance]`

- [x] Nightly message indexing job runs
- [x] Daily summary posts to configured channel
- [x] Weekly game open/close jobs fire; `/support` and `/mission` work with confirmation
- [x] `/vote` creates vote; ballots tallied against threshold



### M6 — Production hardening

- [x] Ollama Modelfile for persona
- [x] Rate limiter + queue tuned under load
- [x] Audit log + health check
- [x] README with deploy steps (venv, ollama pull, systemd optional)


## 15. Post-MVP additions (July 2026)

Implemented after M6; see [`implementation_status.md`](../status/implementation_status.md)
(Post-MVP round + Planning pass P1–P15). Deferred leftovers: [`post_mvp.md`](../status/post_mvp.md).

| Area | Deliverable |
| ---- | ----------- |
| Privacy | `activity_traces` on `/forgetme` |
| Identity | `member_aliases`, `identity_links`, `/identity`, `profile_json` |
| Platform | Capability scan, `/thread`, `/poll`, `/say`, `/son`, `/mode`, `/todo` |
| Coordination | Discord scheduled events on `/event` + `game_week_open` |
| Game | `/support` move/withdraw, invest window, `/game-week` |
| Ecosystem | `/mondo` stats/knowledge/entity, `entity_updates`, public RAG export |
| Matchmaking | Hourly `propose_echoes` job (inbox only) |
| Agent | Dual harness, tool failure feedback, `get_guild_metadata` |
| Governance | Moderation DM suggestions (`governance.escalation_threshold`) |
| Ops | `discord_errors.py`, expanded `/health`, `DISCORD_LOG_LEVEL` |
