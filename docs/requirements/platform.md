# Platform `[platform]`

Part of the [requirements](README.md) for the Tramice721 Discord bot. Requirements use **MUST** / **SHOULD** / **MAY** (RFC-2119 sense).

Discord surfaces, triggers, and delivery constraints.


| ID    | Requirement                                                                                                                                                                                                                  |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PLT-1 | MUST operate in shared Discord **salons (channels)** as a many-humans-to-one-AI social assistant.                                                                                                                            |
| PLT-2 | MUST support **one-on-one DMs** as a private "personal tramice" session. (Members may need to accept the bot to receive DMs.)                                                                                                |
| PLT-3 | MUST support configured triggers: prefix (`!ai`), `@mention`, and slash commands (`/ask`, `/summarize`, etc.).                                                                                                               |
| PLT-4 | MUST be able to send DMs to server members and MAY send `@everyone` announcements (gated behind config / permission; used sparingly).                                                                                        |
| PLT-5 | MUST **not reply to other bots**.                                                                                                                                                                                            |
| PLT-6 | MUST only act in channels it is granted access to (Discord permissions plus bot-side **interact** allow/deny list). Logging MAY use a separate **log** allowlist. `[administration]` |
| PLT-7 | Behavior MUST differ by surface: **DM** = personal-tramice mode (well-being check → wishes); **salon** = community mode (enthusiasm, emojis; intervenes with solutions only when asked or when mediation helps). `[persona]` |


**Operational (cross-cutting):** `[platform]` `[administration]`


| ID     | Requirement                                                                                                                                                                        |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PLT-8  | Local-first / self-hostable (Ollama, CPU-only ~15 GB RAM): 7B model ceiling; multi-second latency; single in-flight request → per-user/channel **rate limiting + queue** required. |
| PLT-9  | Resilient to Discord/Ollama restarts; persistent history and checkpoints. `[community-memory]`                                                                                     |
| PLT-10 | Multi-server-ready in spirit: anticipate several Discord servers / tramices exchanging data ("la course tramicielle"). Not required for first milestone.                           |
