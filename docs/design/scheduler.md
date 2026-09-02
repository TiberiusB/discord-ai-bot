# Scheduler jobs

Part of the [design documentation](README.md) for the Tramice721 Discord bot. Section numbers are kept from the original single-file specification so that `§n` references elsewhere in the docs stay meaningful.

## 8. Scheduler jobs `[game]` `[community-memory]` `[knowledge]`


| Job ID                   | Cron (Montreal) | Action                                      |
| ------------------------ | --------------- | ------------------------------------------- |
| `index_new_messages`     | `0 2 * * *`     | Embed unindexed messages → Chroma `history` |
| `refresh_knowledge_base` | `0 3 * * 0`     | Re-ingest `docs/` if changed                |
| `refresh_web_sources`    | `30 3 * * 0`    | Re-crawl all active `web_sources` → Chroma `web` |
| `build_daily_summary`    | `0 8 * * *`     | Post summary to `summary_channel_id`        |
| `game_week_open`         | `0 17 * * 4`    | Open investment window; announce budgets; optional Discord event |
| `game_week_close`        | `59 23 * * 0`   | Close window; finalize allocations          |
| `propose_echoes`         | `0 * * * *`     | Hourly synergy batch → Échos inbox (no DMs) |
| `capability_scan`        | `0 4 * * *`     | Refresh `data/capabilities.json` (post-MVP) |


All jobs log start/end + row counts to structured logger.
