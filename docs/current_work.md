# Current work

## Next up: V2, the reliable console

Scoped 2026-08-25 with Frédo and Soushi. The problem being solved is that Tramice invents data, which also corrupts her identification of who she is talking to, and that the Game cannot really be played through conversation because the agent cannot reach the services that hold the data.

- Requirements: [`requirements_v2.md`](requirements_v2.md)
- Acceptance test set: [`acceptance_questions.md`](acceptance_questions.md)
- Command reconciliation against Frédo's specification: [`command_inventory.md`](command_inventory.md)

Explicitly deferred: the datastructure redesign (`Tramices`, `Wishes`, `Anon_index`, `Volios`, `Events`), the transport gateway, `/game`, and the stylistic complaints listed in `requirements_v2.md` § 6.

## Previous pass: P1 to P15

All P1 to P15 items from the July 2026 planning pass are implemented. See
[`implementation_status.md`](implementation_status.md).

| Pri | Task | Status |
|---|---|---|
| P1 | Slash renames + `/my-model` | Done |
| P2 | `log_allowlist` / `interact_allowlist` | Done |
| P3 | Invest window + HOP reallocation (`/support`) | Done |
| P4 | Architecture `/game-week` | Done |
| P5 | Schema gaps (`profile_json`, metadata) | Done |
| P6 | Enterprise dashboard + `entity_updates` | Done |
| P7 | `/todo` channel lists | Done |
| P8 | System prompt first person | Done |
| P9 | Dual harness (procedural vs creative) | Done |
| P10 | `/mode` per channel | Done |
| P11 | Tool failure feedback | Done |
| P12 | Hourly matchmaking to Échos | Done |
| P13 | `/mondo view:stats` | Done |
| P14 | Public RAG export + `/mondo view:knowledge` | Done |
| P15 | Guild metadata tools | Done |

Two of these are reported broken from the lab and are re-opened as R6.2 and R6.3 in the V2 requirements: `/todo` reports an empty list where tasks exist, and `/mode` hides its options until clicked.

## Smoke checklist (manual)

- [ ] Sync slash commands after deploy (guild restart)
- [ ] `/support place` during invest window; rejected when closed
- [ ] ToDo salon: bot logs but does not reply; `/todo` works
- [ ] `/mode` + agent turn uses expected harness
- [ ] Hourly job creates Échos (no DMs)
