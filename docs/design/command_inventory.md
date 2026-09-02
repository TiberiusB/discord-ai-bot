# Command inventory: code against Frédo's specification

Reconciliation of the slash commands registered in `bot/commands.py` against the command list in the **Work in progress** tab of the project working document (Google Doc `1LR_x6Px...`, read at its 2026-08-26 01:34 revision).

This file exists because "make sure the existing commands work" means two different things depending on which side you read from, and the two lists overlap less than either side assumes.

## Counts

| Source | Count |
|---|---|
| Registered in `bot/commands.py` | 25 top-level, plus the `web-source` group (`add`, `list`, `remove`) |
| Specified in the working document | 21 |
| Present in both | 8 |

## Present in both

These are the commands a tramarade can use today and that the specification also describes. They are the ones the reliable-console work must guarantee.

| Command | Code | Note |
|---|---|---|
| `/volio` | `bot/commands.py:638` | Spec asks for the alias `/wish`. Not implemented. |
| `/echoes` | `bot/commands.py:788` | |
| `/mission` | `bot/commands.py:1169` | |
| `/mondo` | `bot/commands.py:689` | |
| `/mode` | `bot/commands.py:530` | Spec-side complaint: options do not appear until clicked. |
| `/todo` | `bot/commands.py:1471` | Spec-side complaint: reports an empty list when the salon has tasks. |
| `/support` | `bot/commands.py:1228` | Spec calls it `/sup` or `/support`. Spec requires a checksum-verified arithmetic log. |
| `/game-week` | `bot/commands.py:1540` | Partial match only. The spec's `/game` sets the universal game parameters; `/game-week` sets one week's. They are not the same command. |

## Specified but absent

Thirteen commands appear in the working document and nowhere in the code.

`/alarm` · `/comment` · `/dico` · `/enterprise` · `/freq` · `/help` · `/idea` · `/infos` · `/note` · `/quest` · `/report` · `/team` · `/week`

Of these, `/week` is in scope for the next version by decision of 2026-08-25. `/game` is explicitly deferred. The other eleven are unscheduled.

## Implemented but unspecified

Seventeen top-level commands plus one group exist in the code without a counterpart in the document. Most are operational rather than game-facing.

`/ask` · `/event` · `/forgetme` · `/health` · `/identity` · `/model` · `/my-model` · `/norms` · `/poll` · `/reindex` · `/say` · `/set-norm` · `/signal` · `/son` · `/summarize` · `/thread` · `/vote` · `web-source add|list|remove`

This is not drift to be deleted. Several of these commands are load-bearing (`/identity` is what links a Discord account to a `#trammer`; `/model` and `/my-model` are the model gateway in practice). It is drift to be **documented**, so the working document stops describing a smaller bot than the one that runs.

## Renames the working document asks for

| Current | Requested | Status |
|---|---|---|
| `/signal` | `/report` | Not done |
| `/son` | `sound`, or removed entirely | Not done |
| `/identity` parameters (`membre`, `autre`) | English parameter names | Not done. See `bot/commands.py:994`. |
| `/volio` | add alias `/wish` | Not done |

## How to keep this file true

Regenerate the code side with:

```bash
grep -oE '@tree\.command\(\s*name="[a-z-]+"' bot/commands.py | grep -oE '"[a-z-]+"' | tr -d '"' | sort
```

The specification side has no machine-readable source; it lives in the working document's **Work in progress** tab under `**Slash Commands**` and has to be reread when that tab changes.
