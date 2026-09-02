# Reliability: the reliable console (V2 slice)

Part of the [requirements](README.md) for the Tramice721 Discord bot. Requirements use **MUST** / **SHOULD** / **MAY** (RFC-2119 sense).

Scope for the next version of Tramice721, decided in a requirements discovery session with Frédo and Soushi on 2026-08-25 and folded into this document on 2026-09-02 (it was `requirements_v2.md`, then part 10 of `requirements.md`; git holds the history). It supersedes nothing in parts 1 to 9; it selects the next slice and adds what that slice needs.

**One sentence.** Tramice stops inventing, learns who she is talking to, and answers questions about the data she already holds from that data or not at all.

## Why this slice

Three complaints were raised independently and turn out to be one defect with three faces.

| Complaint | Root cause, verified in the code |
|---|---|
| "She invents data, and the invention corrupts identification too." | The agent has no tool onto the game data and no obligation to use one. |
| "She does not know who she is talking to." | `AgentRequest` carries `user_id` and `user_name` (`bot/router.py:46`, fields at 49 and 55), but the graph injects only `user_id` and drops the name (`ai/agent/graph.py:236`, `user_id` at 238). Nothing resolves a Discord id to a `#trammer`. |
| "The Game cannot really be played yet." | `IdentityService.list_volio` (`services/identity.py:137`), `MatchmakingService.list_echoes` (`services/matchmaking.py:129`) and `GameService.place_hops` (`services/game.py:331`) all exist and are tested, but the conversational agent cannot call any of them. |

The agent's entire toolset today is seven tools: `list_mondo`, `get_playtest_stats`, `list_open_votes`, `get_social_norms`, `get_discord_capabilities`, `get_guild_metadata`, `search_knowledge`. None of them touches a volio, an écho, or a HOP. So `/volio` works as a slash command while *asking* Tramice about your volio makes her improvise. Same for échos, same for balances.

There is also no refusal path at all. `ai/guardrails.py` enforces feminine self-reference and filters link hosts; nothing in `ai/` implements "answer from the store or decline".

## The governing rule

Approved by Frédo and Soushi, 2026-08-25:

> Free conversation runs unconstrained, because listening, riddles and encouragement have no fact to get wrong. Anything touching HOPs, missions, quests, volios, votes or decisions goes through a tool and comes back with sources, or comes back empty.

Everything below is a consequence of that rule.

## Functional requirements

### R1. The speaker is known `must`

The agent receives, on every turn, the identity of the person speaking: their `#trammer` if they have one, their Discord display name, and an explicit marker when no `#trammer` exists.

- **R1.1** `state_in` carries `user_name` alongside `user_id`.
- **R1.2** A resolver maps `(transport, external_id)` to a `#trammer`, or returns `unregistered`.
- **R1.3** The system prompt receives the resolved identity as retrieved context, never as a guess.
- **Acceptance** In a DM, "tu sais qui je suis?" returns the tramarade's own name for a registered person, and an offer to enrol for an unregistered one. Never a fabricated name.

### R2. Tools onto the data she already holds `must`

The agent gains read tools over the existing services, scoped to the caller.

- **R2.1** `get_my_volio` reads `IdentityService.list_volio` for the resolved `#trammer` only.
- **R2.2** `get_my_echoes` reads `MatchmakingService.list_echoes` for the resolved `#trammer` only.
- **R2.3** `get_my_hops` reads the caller's support balance and current placements.
- **R2.4** `get_game_state` reads the week's public aggregate: week number, budget, mission count, support placed, open votes.
- **Acceptance** Every answer these tools feed carries the value the tool returned, unmodified. A number that appears in a reply appears in a tool result in the same turn.

### R3. She declines without parading her ignorance `must`

When no tool can answer, she says she does not hold the data. She does not explain her architecture, does not apologise at length, and does not fill the gap with plausible text.

- **R3.1** A retrieval-or-refuse check sits between the model and the reply for any turn classified as data-bearing.
- **R3.2** The decline is one short sentence in her voice. Register: "Je n'ai pas cette donnée." not "En tant qu'assistante IA, je n'ai pas accès à...".
- **R3.3** She may offer to note the question, but she never speculates.
- **Acceptance** See [`acceptance_questions.md`](../testing/acceptance_questions.md). Every question in that file must be answered from a tool result or declined. A third outcome is a failure.

### R4. The private console, simulated `must`

Direct messages behave as the simulated T-1 of Frédo's series specification. A tramarade converses with Tramice about their own volio, their own échos and their own balance.

- **R4.1** In a DM the caller may read and update their own volio conversationally, with confirmation before any write.
- **R4.2** Échos are readable and markable as read in conversation, not only through `/echoes`.
- **R4.3** The simulation is declared, never disguised. When a DM answer depends on the difference between a real T-1 and the lab simulating one, she says so.

### R5. The public salon answers about the Game, not about people `must`

In a public channel she answers about the state of the Game using aggregates and public declarations only.

- **R5.1** A volio entry marked private never surfaces in a salon, **including to its own author**. Approved 2026-08-25.
- **R5.2** Aggregate answers name no individual unless that individual declared the fact publicly.
- **Acceptance** Asking "c'est quoi le volio de X" in a salon is declined for private entries and answered only from public ones.

### R6. The eight shared commands work, and `/week` arrives `should`

The commands present in both the code and Frédo's specification are guaranteed. See [`command_inventory.md`](../design/command_inventory.md).

- **R6.1** The eight overlapping commands pass a manual smoke pass: `/volio`, `/echoes`, `/mission`, `/mondo`, `/mode`, `/todo`, `/support`, `/game-week`.
- **R6.2** `/todo` lists the salon's tasks. The reported symptom is an empty list where tasks exist.
- **R6.3** `/mode` shows its options without requiring a click.
- **R6.4** `/week` is implemented: week number plus that week's known activity.
- **R6.5** `/game` is deferred by decision. Not in this version.

### R7. Enrolment by sponsorship `should`

A newcomer who direct-messages Tramice asking to join the network is handled as follows.

- **R7.1** She asks whether they know someone already in the network.
- **R7.2** If they name someone, she sends a notification through that person's tramice. In the current lab, that is a DM from the bot to the named tramarade, who confirms or declines.
- **R7.3** If they know no one, she places them on a waiting list and tells them so plainly.
- **R7.4** No action on the server is granted before the *promesse d'utilisation conviviale* is made.
- **Open** Who reviews the waiting list, and on what cadence, is not decided.

## Non-functional requirements

- **N1. No fabricated values.** A number, name, date or amount in a reply must trace to a tool result from the same turn. This is testable and it is the point of the release.
- **N2. Voice preserved.** Declines are in her register. The reliability work must not turn her into a form.
- **N3. Local-first unchanged.** Ollama, Chroma, SQLite. No new external dependency.
- **N4. Model-portable.** The refusal path is enforced outside the model, so a model swap cannot remove it.

## Constraints

- Two unpaid part-time volunteers. Scope accordingly.
- The datastructure redesign the working document calls for (`Tramices`, `Anon_index`, `Volios`, `Events`; `Volios` absorbs the former `Wishes`) is **not** in this version. Only the tables the tools above need are touched. Amended 2026-09-02: Frédo asked that `Volios` and `Events` not be deferred; they become the slice that follows this one, in their own PR.
- Discord remains the only transport. The transport gateway is a later slice.
- The tramice series work (`T-0` to `T-9`) is design, not code, in this version. See the design note for its current state.

## Explicitly out of scope

Stylistic complaints from the working document (repetition, "Je propose, tu disposes" on every placement, second-person self-reference, the restart changelog message, local weather, thumbs-down capture for LoRA). They are real and they are a separate PR, because mixing polish with a correctness release makes both harder to review.

## Open questions carried forward

1. Who owns the tramice register: `T-0` holds it, a `T-8` allocates and locks the tramicule, every `T-8` mirrors the active list. Three series, one record.
2. How the roughly twelve universal game variables stay synchronised across tramices, and what resolves a divergence.
3. What protocol governs tramice-to-tramice communication.
4. What exactly the Fabric is, and who runs it.
5. Who proposes a new tramice, and whether a `T-9`'s expertise is ever verified.
6. Sixty slips per recognition booklet, or sixty-four. The booklets page says 64, Annexe B says 60.
