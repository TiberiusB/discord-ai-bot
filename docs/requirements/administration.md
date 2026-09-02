# Administration `[administration]`

Part of the [requirements](README.md) for the Tramice721 Discord bot. Requirements use **MUST** / **SHOULD** / **MAY** (RFC-2119 sense).

Operator-facing configuration and maintenance.


| ID    | Requirement                                                                                           |
| ----- | ----------------------------------------------------------------------------------------------------- |
| ADM-1 | MUST support **model swap** (config + `/model` command) — the tramice "soul" is replaceable. Per-user override via `/my-model`. |
| ADM-2 | SHOULD support manual `/reindex` (scoped: docs, web, or all), `/web-source` curation, and scheduled indexing/summaries. `[knowledge]` `[community-memory]` |
| ADM-3 | SHOULD expose channel allow/deny list and feature flags via `config.yaml` / `.env`.                   |
| ADM-4 | SHOULD gate `@everyone` announcements behind explicit permission/config. `[platform]`                 |
