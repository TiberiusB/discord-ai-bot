# Game `[game]`

Part of the [requirements](README.md) for the Tramice721 Discord bot. Requirements use **MUST** / **SHOULD** / **MAY** (RFC-2119 sense).

Weekly cycle simulation and HOP workflow.

The bot SHOULD help the community *simulate* the game loop. Ledger accuracy is
"best-effort simulation" for the playtest, not a production financial system.


| ID    | Requirement                                                                                                                                                                   |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GME-1 | SHOULD be aware of the **weekly cycle**: Missions announced by **Thursday 17:00**; investment window **Thursday 17:00 → Sunday midnight**; budgets finalized Sunday midnight. |
| GME-2 | SHOULD help enterprises publish **Missions** (HOP + material needs) and help trammers track enterprises they support. `[identity]` `[ecosystem-mapping]`                      |
| GME-3 | SHOULD support **quests** (unforeseen, real-time needs) and their retroactive recognition the following week.                                                                 |
| GME-4 | MAY compute/announce the weekly **support budget** (*budget d'appui*, formerly "budget d'influence"; avg of previous week's HOPs +20%, min 5, max 100) and the **AUM** (5 HOPs).                                             |
| GME-5 | Any HOP/booklet figures the bot reports MUST respect rules in §5.2–§5.3 (no negative balances, hundredths precision, individual cap 99 999,99 HOPs).                          |
| GME-6 | SHOULD explain physical **booklets** (Recognition, Mission, Quests, Allocation) without replacing them. `[knowledge]`                                                         |


**Domain concepts:** HOP, weekly cycle, booklets, AUM, support budget (*budget d'appui*). See §5.2–§5.3.

## HOP — the currency `[game]`

- Time-based unit ("one hour of work by a person"); *une heure reste une heure*.
- **Indicative & negotiable**: hard/painful work MAY count as 2–3+ HOPs by agreement.
- Divisible **to hundredths only** (2 decimals).
- Created **only to recognize peer-validated work**; booklets **cannot go negative**.
- **Individual cap: 99 999,99 HOPs** per carnet. Max **100 HOPs** investable per person/week.
- A "monnaie-processus": legitimacy = propose → vote → work → peer-validate → recognize.

## Weekly cycle `[game]`

- **Thursday 17:00:** support budget per trammer = avg HOPs created previous week **+20%** (adjustable); **min 5, max 100**. Enterprises post **Missions**.
- **Thursday → Sunday midnight:** investment window. Placements in enterprises **other than own**. Unplaced HOPs auto-distribute along trend, capped by enterprise requests.
- **Sunday midnight:** allocations finalized into **Booklets de Mission**. HOPs become real only after peer-validated work. Unused Mission HOPs evaporate (no carry-over without extension).
