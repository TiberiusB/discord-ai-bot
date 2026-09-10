# Governance `[governance]`

Part of the [requirements](README.md) for the Tramice721 Discord bot. Requirements use **MUST** / **SHOULD** / **MAY** (RFC-2119 sense).

Decision-making, norms, conflict resolution, and deliberation support.

### Decision-making `[governance]`


| ID    | Requirement                                                                                                                      |
| ----- | -------------------------------------------------------------------------------------------------------------------------------- |
| GOV-1 | SHOULD help **facilitate collective votes** and seek consensus, reflecting game governance (e.g. 80% threshold to change rules). |
| GOV-2 | MUST NOT decide, vote, or transact on anyone's behalf. `[matchmaking]` `[game]`                                                  |
| GOV-3 | MUST NOT be used for vote manipulation or bot-farm behavior.                                                                     |




### Deliberation & mediation `[governance]` `[community-memory]`


| ID    | Requirement                                                                                                                                            |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| GOV-4 | MUST provide **server-activity summaries** and, on demand, **synthesize debates** — mapping points of view and arguments (subject to peer validation). |
| GOV-5 | SHOULD offer gentle **mediation** when a salon conversation turns heated. `[persona]`                                                                  |
| GOV-6 | SHOULD mediate conflicts first (tramice as mediator), before escalating to ad hoc tribunal workflow.                                                   |




### Conflict resolution `[governance]`


| ID    | Requirement                                                                                                                                             |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GOV-7 | SHOULD support **ad hoc tribunal** workflow: jury of 7 trammers drawn by lot (paid in HOPs), motivated transparent decisions, jurisprudence catalogued. |
| GOV-8 | SHOULD implement **random selection** of available, non-conflicted trammers for juries and similar roles. `[coordination]`                              |
| GOV-9 | SHOULD support graduated **signaling** (reporting): discomfort → clear breach → immediate danger; abusive reports are themselves a breach.              |




### Social norms `[governance]`


| ID     | Requirement                                                                                                                                                    |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GOV-10 | SHOULD maintain configurable **social norms** defining what topics/data are always private vs always public. Norms MUST be readable by all trammers.           |
| GOV-11 | SHOULD provide **admin-invokable bot functions** (slash commands or equivalent) for server admins to adapt social norms. `[administration]`                    |
| GOV-13 | A change to the Game's design relative to the founding proposal (*Un jeu pour système*, latramice.net, January 2026) MUST be made by a tramarade holding the **@Architecture** role in the lab. Frédo, 2026-09-02. |
| GOV-12 | Bot actions (logging, summarizing, matchmaking, profile display) MUST be coherent with current social norms. `[community-memory]` `[identity]` `[matchmaking]` |


> **TODO:** Propose infrastructure for private/public delineation based on social
> norms; harness for bot actions that respect them. `[governance]` `[platform]`



### Ethical charter (Annexe A) `[governance]` `[persona]`

The bot SHOULD embody the *Engagements tramiciels*:

- Respect personal sovereignty (clear, early "no" without justification required).
- Transparency of intentions in proposals (expected, offered, risks).
- Fair recognition — discourage predatory HOP demands and "OneStar" undermining.
- Protect the vulnerable; never exploit, harass, or belittle vulnerability.
- Preserve the commons: no spam / info-pollution.
- Right to error & repair: understanding → repair → reintegration over exclusion.

**Domain concepts:** AUM vote, 80% rule changes, parrainage, trust capital, tribunal, transparency exceptions. See §5.5.

## Governance & transparency rules `[governance]` `[game]`

- **AUM:** 5 HOPs/week unconditional, essential goods/services only; re-voted yearly.
- **Rule changes:** **80%** transparent vote (threshold itself changeable).
- **Identity verification:** **parrainage** (existing trammer vouches).
- **Trust capital:** key non-monetary currency; fraud destroys it.
- **Conflict resolution:** tramice mediates → ad hoc tribunal (jury of 7, lot-drawn, paid in HOPs) → jurisprudence.
- **Transparency by default**, with exceptions the bot MUST respect:
  1. confidences to the tramice; 2. private messaging; 3. personal addresses (optionally hidden);
  2. transaction details may stay general; 5. network data internally verifiable, opaque externally.
