# Documentation

Documentation for the Tramice721 Discord bot, organised by what each document is for. The root [`README.md`](../README.md) covers installation and operation; this folder covers what the bot must do, how it is built, and where the work stands.

Everything under `docs/` is ingested into the bot's knowledge base (`python -m ai.rag.ingest` walks the tree recursively), so a document placed here is also a document Tramice can cite.

| Folder | Contents | Read it when |
|---|---|---|
| [`game/`](game/) | `jeu.pdf` (the game design, "Un jeu pour système"), `Discord and AI.pdf` | You need the source the requirements were extracted from |
| [`requirements/`](requirements/) | [`README.md`](requirements/README.md) (context, catalog, index), one file per domain, [`reliability.md`](requirements/reliability.md) for the current slice | You want to know what the bot must do and why |
| [`design/`](design/) | [`specifications.md`](design/specifications.md), [`command_inventory.md`](design/command_inventory.md) | You want to know how it is built, and how the commands map to Frédo's specification |
| [`testing/`](testing/) | [`acceptance_questions.md`](testing/acceptance_questions.md) | You are checking whether a release is reliable |
| [`status/`](status/) | [`current_work.md`](status/current_work.md), [`implementation_status.md`](status/implementation_status.md), [`planning.md`](status/planning.md), [`post_mvp.md`](status/post_mvp.md) | You want to know what is built, what is next, and what was deferred |
| [`operations/`](operations/) | [`ai_logging_notice.md`](operations/ai_logging_notice.md) | You are putting the bot on a server and must inform its members |

Start with [`status/current_work.md`](status/current_work.md): it names the slice in progress and links to the documents that define it.
