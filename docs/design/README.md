# Design: Tramice721 Discord Bot

> Technical specification derived from [`requirements/`](../requirements/README.md).
> These documents define **how** the system is built. Requirements define **what**
> it must do. The implementation plan (the original milestone plan, M0 to M6)
> defines **when** (milestones M0–M6).


| Field               | Value                                              |
| ------------------- | -------------------------------------------------- |
| Version             | 0.2                                                |
| Status              | Implemented (M0–M6 + post-MVP July 2026)             |
| Primary runtime     | Python 3.12, discord.py 2.7, Ollama (local)        |
| Default LLM         | `qwen2.5:7b-instruct` (per-user override: `/my-model`) |
| Default embed model | `nomic-embed-text`                                 |
| Target environment  | CPU-only, ~15 GB RAM, single Ollama inference slot |


---

---

## Files

| File | Sections | What it covers |
|---|---|---|
| [`architecture.md`](architecture.md) | [§2](architecture.md), [§3](architecture.md) | Architecture |
| [`data-model.md`](data-model.md) | [§4](data-model.md) | Data model |
| [`services.md`](services.md) | [§5](services.md) | Service modules |
| [`agent-tools.md`](agent-tools.md) | [§6](agent-tools.md) | Agent tools and MCP servers |
| [`discord-interface.md`](discord-interface.md) | [§7](discord-interface.md) | Discord interface |
| [`scheduler.md`](scheduler.md) | [§8](scheduler.md) | Scheduler jobs |
| [`configuration.md`](configuration.md) | [§9](configuration.md) | Configuration |
| [`security-privacy.md`](security-privacy.md) | [§10](security-privacy.md), [§11](security-privacy.md) | Security, privacy, guardrails and observability |
| [`command_inventory.md`](command_inventory.md) | | Registered slash commands against Frédo's specification |
| [`../status/milestones-2026-07.md`](../status/milestones-2026-07.md) | [§12](../status/milestones-2026-07.md), [§15](../status/milestones-2026-07.md) | Milestone acceptance criteria and post-MVP additions (history) |

---

## 1. Traceability

Each design file maps to requirement service tags and IDs. The original single-file table was one section off from its own headings; this one is rebuilt from the files as they are.

| Design file | Sections | Services | Requirement refs |
| --- | --- | --- | --- |
| [`architecture.md`](architecture.md) | §2, §3 | all | [`requirements/README.md`](../requirements/README.md) service catalog |
| [`data-model.md`](data-model.md) | §4 | `[identity]` `[game]` `[community-memory]` `[governance]` | IDN-*, GME-*, MEM-*, GOV-10…12 |
| [`services.md`](services.md) | §5 | per service | one file per domain under [`requirements/`](../requirements/README.md) |
| [`agent-tools.md`](agent-tools.md) | §6 | all core | [`reliability.md`](../requirements/reliability.md) R2, R3 |
| [`discord-interface.md`](discord-interface.md) | §7 | `[platform]` `[administration]` | PLT-*, ADM-* |
| [`scheduler.md`](scheduler.md) | §8 | `[game]` `[community-memory]` `[knowledge]` | GME-*, MEM-4, ADM-2 |
| [`configuration.md`](configuration.md) | §9 | `[administration]` | ADM-*, PLT-8…10 |
| [`security-privacy.md`](security-privacy.md) | §10, §11 | `[governance]` `[community-memory]` | GOV-*, MEM-*, NFR-* |
| [`../status/milestones-2026-07.md`](../status/milestones-2026-07.md) | §12, §15 | all | milestones M0 to M6 |
---

## 13. Out of scope (v1)

Per requirements [§8](scheduler.md): graphical Mondo UI, distributed HOP ledger, legal/tax
accounting, physical booklets, biometric identity, multi-server sync protocol.

---

## 14. Open decisions (blockers)


| #   | Decision                                      | Status / recommendation        |
| --- | --------------------------------------------- | ------------------------------ |
| 1   | `GUILD_ID` + `summary_channel_id`             | Set in lab deployment          |
| 2   | `log_allowlist` vs `interact_allowlist`       | Set in lab deployment          |
| 3   | Game enforce vs assist                        | **Assist** for playtest        |
| 4   | Default LLM soul                              | `qwen2.5:7b-instruct`; `/my-model` for experiments |
| 5   | `@everyone` enabled?                          | Deferred; capability tracked   |
| 6   | Default social norms for playtest             | Seeded in [§9.3](configuration.md); `/set-norm`    |

---

## 16. Glossary (spec usage)


| Term    | Spec meaning                                               |
| ------- | ---------------------------------------------------------- |
| Trammer | Discord server member / player. *Tramarade* is the French equivalent per Frédo's lexicon; English docs use either, French strings always *tramarade* |
| Tramice | Personal AI console; this bot simulates it                 |
| Volio   | Profile chest: wishes, talents, offers, requests           |
| Échos   | Matchmaking inbox notifications                            |
| Mondo   | Ecosystem map (text/embed rendering on Discord)            |
| HOP     | Hour of work unit (simulated, 2 decimal places)            |
| Entity  | DB row: enterprise, quest, mission, event, place, or idea  |
| Surface | `salon` (channel) or `dm` (direct message)                 |
