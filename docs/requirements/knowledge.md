# Knowledge `[knowledge]`

Part of the [requirements](README.md) for the Tramice721 Discord bot. Requirements use **MUST** / **SHOULD** / **MAY** (RFC-2119 sense).

Grounded answers and document retrieval.


| ID    | Requirement                                                                                                                                                                                               |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| KNW-1 | MUST answer factual questions about the game, the Guilde, the dashboard, and the local universe, grounded in project documents (`jeu.pdf`, charter, annexes) via RAG over `docs/`, not from memory alone. |
| KNW-2 | When uncertain, MUST hedge and attribute sources (NORA; "never affirm what is not 100% certain"). `[persona]`                                                                                             |
| KNW-3 | SHOULD provide links to LaTramice.net resources where relevant.                                                                                                                                           |
| KNW-4 | SHOULD explain game instruments (booklets, HOP, weekly cycle) accurately when asked. `[game]`                                                                                                             |
| KNW-5 | SHOULD allow admins to register external web sources (seed URLs) for same-domain shallow crawl into RAG; members benefit via grounded `/ask` answers. `[administration]`                               |


**Implemented (July 2026):** admin-curated web RAG via `/web-source add|list|remove`, Chroma `web` collection, scoped `/reindex`, and scheduled `refresh_web_sources`. Primary path for LaTramice.net content — not live browser fetch.

> **TODO (future):** Browser-search MCP for JavaScript-heavy sites. `[knowledge]` `[administration]`
