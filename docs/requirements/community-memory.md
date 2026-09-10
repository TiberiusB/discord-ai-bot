# Community memory `[community-memory]`

Part of the [requirements](README.md) for the Tramice721 Discord bot. Requirements use **MUST** / **SHOULD** / **MAY** (RFC-2119 sense).

Logging, retention, and history-powered features.


| ID    | Requirement                                                                                                                                             |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MEM-1 | MUST log readable messages to a local store to power summaries, matchmaking, and RAG-over-history, honoring channel log allow/deny list (may differ from interact allowlist). `[administration]` |
| MEM-2 | MUST offer a member data-deletion path (e.g. `/forgetme`). MAY retain a minimal activity trace (name, span, count) without message content. |
| MEM-3 | Confidences to the tramice and DMs MUST stay private — not surfaced in public summaries or matchmaking without consent. `[governance]` `[identity]`     |
| MEM-4 | SHOULD post a scheduled **daily/periodic server summary** to a configured channel. `[governance]` `[administration]`                                    |


**Privacy:** logging messages has GDPR-style implications → separate log and
interact allowlists, posted AI-logging notice, deletion command. `[governance]` `[administration]`
