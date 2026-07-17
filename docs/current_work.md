# Immediate improvements — status

All P1–P15 items from the planning pass are **implemented** (July 2026).
Documentation is aligned with the codebase — see
[`implementation_status.md`](implementation_status.md) (Planning pass P1–P15).

## Completed

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
| P12 | Hourly matchmaking → Échos | Done |
| P13 | `/mondo view:stats` | Done |
| P14 | Public RAG export + `/mondo view:knowledge` | Done |
| P15 | Guild metadata tools | Done |

## Smoke checklist (manual)

- [ ] Sync slash commands after deploy (guild restart)
- [ ] `/support place` during invest window; rejected when closed
- [ ] ToDo salon: bot logs but does not reply; `/todo` works
- [ ] `/mode` + agent turn uses expected harness
- [ ] Hourly job creates Échos (no DMs)
