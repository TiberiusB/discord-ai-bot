# The tramiciel protocol

> **Sources.** Frédo's specification in the working document, section *En développement : l'écosystème tramiciel*, and the `Volios`, `Tramices`, `Wishes` and `Anon_index` tables in the same document; his open-questions list in the same tab; the third-pass reading of that specification dated 26 August 2026; the lab session of 9 September 2026. Statements marked **(reading)** are proposals from the development side and are Frédo's to accept or drop.

The protocol is the set of rules by which tramices interact with each other and with people. It says nothing about how any one tramice works inside; each keeps its own system. What it governs is the boundary: who may exist, what a message is, who may speak first, what crosses a border, and what a tramice is entitled to believe from another tramice it did not build.

Frédo's own statement of what it is, from the open-questions list:

> Le Protocole tramiciel est en cours de rédaction ; il s'agit d'un protocole pair-à-pair où le social et l'association économique émergent de l'interindividuel ; l'écosystème tramiciel en est un, essentiellement, de match-making des souhaits (l'appariement des souhaits qui se répondent) et toute entité dans cet éco-système communique par souhaits (plus précisément, par volios), y compris les tramices elles-mêmes, lorsque cela s'applique, c'est-à-dire lorsqu'une intention est impliquée ; exceptions : dialogues libres.

Three things follow from that one sentence, and they are the spine of this page.

1. It is **peer to peer**. The social and the economic association emerge from the interindividual; there is no centre to route through.
2. The **volio is the message**. Every entity communicates by wishes, tramices included, whenever an intention is involved.
3. **Free dialogue is exempt.** Conversation that carries no intention is not protocol traffic.

A sentence from the lab session of 9 September fixes where the protocol lives relative to the software:

> The harness is the tool that manages context. The harness contains the protocol; the protocol is the rules.

So the protocol is something this repository's software must implement, not something it is.

## 1. The volio is the wire format

Because a mission is an intention, missions and quests are announced in the network as volios. The same holds for a tramice with something to say: it emits a volio. The `Volios` table in the working document is what makes this concrete, and three of its fields are the protocol's own:

| Field | Values | Why it is protocol |
|---|---|---|
| `actor_type` | `trammer`, **`tramice`**, `team`, `mission`, `quest`, `enterprise`, `idea`, `event`, `entry`, `place` | A tramice is a first-class author of a volio, not a relay for human ones |
| `is_systemic?` | boolean, glossed *est-ce un signal machine (Tramice) ?* | A machine signal is flagged as such on the wire, so a reader always knows whether a person meant it |
| `scope` | `lab`, `global`, `direct`, `network`, glossed *périmètre de diffusion du volio* | How far a wish is allowed to travel is a property of the wish, decided at emission |

Alongside those: `type_of_wish` (`offer`, `demand`, `need`, `interest`, `question`, `share`, `participate`, `support`, `system`), `visibility` (`public`, `pseudonym`, `anonymous`, `confidential`), `urgency`, `gravity`, and `matches_found` as pairs of temporary identifiers.

The entities that have a volio are named in the document: tramarades, tramices, teams, events, missions, quests, enterprises, ideas, D'ico entries, places, and labs.

**(reading)** `scope` is architecturally load-bearing and currently has no algorithm behind it. Whatever answers [question 03](open-questions.md) has to say what each of its four values does at a border.

## 2. How a tramice comes to exist

| Station | Where | What happens |
|---|---|---|
| **Verify and lock** | at a **T-0** | Before a tramicule may be held, a T-0 checks three things: that the number is not already taken, that the proposed tramice **does not duplicate an existing function**, and that its role is clearly defined |
| **Record** | at a **T-0** | The same series keeps the register of the ecosystem: tramicule, instantiation, responsible tramarade. The `Tramices` table is exactly that shape, plus a postal code and a `date_retired` |
| **Mirror** | across every **T-8** | The register of active tramices counts as universal information and propagates by mirror into every T-8, which is how a tramice in one locality knows a tramice in another exists at all |
| **Discipline** | at a **T-6** | Any tramice may be reported for improper behaviour, and **its responsible humans** must correct course or justify themselves before a tribunal of five to seven tramarades convened through a T-6, consulting the T-0s as needed |

Note that allocation and record sit in the same series. **T-0 is the authority and T-8 is a mirror.** An earlier reading on our side had a T-8 doing the verification, which would have split the record across three series; the specification as it stands does not, and this page follows the specification.

Three consequences are worth stating outright.

**The duplication check makes the register a design constraint rather than a phone book.** A tramicule is refused not only when the number is taken but when the function already exists.

**The accountable party is a person, never the software.** The tribunal summons the humans responsible for a tramice. That is why the register carries a responsible tramarade alongside the number.

**Retirement is in the schema but not in the protocol.** `date_retired` is a field, and Frédo's own open question asks what fills it: *Une tramice peut-elle être « retirée » ? Selon quelles modalités ? Une T-0 vérifie l'attribution, mais qui décide de la fin de vie d'une tramice ?* See [question 04](open-questions.md).

What remains unspecified is who **proposes** a new tramice. The expertise half of that question Frédo has answered, in the T-9 entry: *expertise **is** verified, yet over time and on a free basis: it is attributed and revocable.* The proposing half is open, and Tibi's warning is recorded with it: without a stated process the ecosystem risks going anarchic or being captured by a minority. See [question 05](open-questions.md).

## 3. How a person enters

Enrolment is by sponsorship, and the T-10 series runs it.

1. The T-10 asks the newcomer whether they already know someone in the network.
2. If they name someone, a notification travels **through that person's tramice**. In the current lab that is a direct message from the bot to the named tramarade, who confirms or declines.
3. If they name no one, the T-10 puts them on a waiting list and says so plainly.
4. **No action is permitted on the server before the *promesse d'utilisation conviviale* is made.**
5. The anonymised waiting list goes to a local T-10, which then acts as intermediary.

The specification adds its own warning: *Le protocole est complexe. Une documentation vivante (D'ico enrichi, tutoriels, FAQ) est indispensable.* T-10s carry a training module for new tramarades.

The convivial-use promise is a hard gate, not a formality. It is the only thing standing between arriving and acting.

## 4. Who may speak first

Ten of the eleven series are not peers. The distinction that matters is not what a tramice knows but what it is allowed to initiate.

| Class | Series | May start a conversation? |
|---|---|---|
| **Interface** | T-1, T-7 | These are where people live. A person addresses them; they address the person |
| **Service** | T-0, T-2, T-3, T-4, T-6, T-8, T-9 | No. They answer when called. T-4's rule is explicit: *ne s'adressent pas à nous en premier* |
| **Subscription** | T-5 | Yes, and only because the reader subscribed, and can unsubscribe |
| **Threshold** | T-10 | Answers a newcomer's first message, and reaches a sponsor through that sponsor's own tramice |

Two series break the tiering and both breaks are deliberate. **T-5 initiates**, which no other service does, but only toward someone who asked it to. **T-6 acts on the world**: it convenes juries, allocates space with the T-3s, redistributes teams that split. It is the only series with executive power, and putting it there rather than in T-0 is what keeps the watcher from becoming the judge.

Full per-series detail is in [the catalogue](series.md).

### Raw or interpreted, and the choice is the reader's

A person can always go straight to a service. Ask a T-8 directly and the answer is the generic core of the Trame: raw, true of everyone and about no one in particular. Ask through your T-1, or your lab's T-7, and the same answer arrives with a layer of interpretation shaped by who you are or what your team is doing.

Neither is more correct. The direct path is what you want when you are checking the system; the interpreted path is what you want when you are living in it. Frédo's own line for the same idea: *en principe, les tramarades pourront naviguer l'écosystème avec une T-1 sans avoir à connaître toutes les catégories de tramices*.

## 5. The channel between a console and a lab

A T-7 may send messages to the T-1s of the lab's members, and **those members filter them on their own T-1**. The channel runs both ways: a personal session can send a finding to a project's lab, and a lab session can ask a console to update its tramarade's volio with what was just decided.

**(reading)** The one rule that makes this safe: what crosses the channel is a **request**, never a write. A lab asking your console to change your volio produces something you approve, not something that has already happened. The filter the specification puts on the T-1 end is the same boundary seen from the other side: the private space decides what enters as well as what leaves.

On Discord this lives naturally in direct messages, which is where a console belongs anyway.

## 6. How a wish crosses a boundary

A T-1 publishes its tramarade's volios anonymised, with a temporary identifier of a different format, **and it alone holds the key**. `Wishes` holds a description and a `temp_ID` and never a person; `Anon_index` maps that identifier back to the real one, is annotated *must be kept private in T-1s*, and identifiers are anonymised separately for each wish, so two wishes from the same person do not correlate.

| Stage | Where | What is visible |
|---|---|---|
| **Publish** | the tramarade's own console | The console decides what leaves the private space at all, and mints the temporary identifier. Nothing downstream sees more than this |
| **Match** | a T-8 | Works on published, de-identified wishes and records `matches_found` as pairs of temporary identifiers. It cannot resolve either side |
| **Introduce** | the two consoles | Re-identification happens where the keys are, with both parties agreeing. This is where a person appears, and it is the only place they can |

The matcher genuinely sees shapes, not people.

Frédo has already recorded the failure mode and a proposed remedy: *Le système d'ephemeral_id repose sur la confiance dans la T-1 [...] Que se passe-t-il si une T-1 est compromise ou si un.e tramarade perd l'accès à sa clé ? Proposition : prévoir un mécanisme de récupération d'urgence via une T-6, avec vérification d'identité par un jury. Vérifier d'abord via le parrainage.* Recovery therefore runs through the same two institutions as everything else contested: the sponsor chain first, then a jury. See [question 06](open-questions.md).

## 7. Locality, and what travels

Every tramice is located by a postal code and bound to the matching timezone. A T-1 follows its tramarade as they move, so the game's temporal milestones line up with their local hour. This is what turns a fleet into a federation.

| Class | What | Rule |
|---|---|---|
| **Stays local** | Local information: shared objects and vehicles, coordinated with the T-3s | A wish is answered where it was made; the local mirror is the whole world as far as it is concerned |
| **Travels, with consent** | Unresolved non-local wishes | A wish that finds no local answer **may** propagate to neighbouring T-8s, *avec l'approbation de leurs auteurs*. Reach is a decision the author makes, not a property of the network |
| **Mirrors everywhere** | Language entries after collective approval, and the register of active tramices | These propagate by mirror into every T-8. This is the WOOM |

### The synchronisation question

Frédo's own question: *Comment synchroniser les variables universelles du jeu (budget, activité, majorité, ~ 12 en tout) entre les tramices ? Quelle est la formule pour éviter (ou sinon : résoudre) des divergences entre les versions tenues pour vraies par les différentes tramices ?*

**(reading)** Our answer, offered rather than assumed: **the variables are not replicated state, they are derived from a shared log of events.** Two tramices that read the same booklet chain compute the same budget, and if they do not, the disagreement is an alarm rather than a merge conflict. See [question 02](open-questions.md).

## 8. Tramice to tramice

The message shape is settled: a volio, flagged `is_systemic?`, carrying a `scope`. What is not settled is transport and trust, and the hard half is trust: **what a tramice is entitled to believe from another tramice it did not build.**

Frédo's founding letter already names the first two things that should cross a lab boundary: wishes the local tramarades could not answer, and new lexicon entries, so that tramices enrich each other's dictionaries.

**(reading)** Our position on the trust half: signed, fetchable artifacts with a validity window, never live calls, and no tramice trusted because of who sent the message. Three reasons.

- A tramice that answers calls becomes the hottest dependency in a network built to avoid a centre, and takes it down when it stops.
- Cached artifacts survive several independent tramices disagreeing, which is the point: agreement between independent witnesses is the signal, disagreement is an alarm that fires without anyone holding authority.
- Every tramice reports to an associated T-0, so a synchronous register would put the whole ecosystem behind one write path.

The transport is the easy half and is partly a platform accident: Discord blocks bot-to-bot messaging directly, and webhooks route around it. See [question 03](open-questions.md).

## 9. What must hold in every tramice

The specification contains a note about where the shared parts belong:

> the register, persona loading, memory and tool scoping, retrieval-or-refuse (knowing how to say « Je ne sais pas. »), should be written as Fabric core rather than lab code, so the next series inherits it instead of reimplementing it.

That is the clearest statement in the corpus that the protocol is implemented once, at a substrate level, and inherited. It is explicitly not where the lab's bot code should live, which makes it a constraint no amount of reading this repository would surface.

Three invariants follow, and none of them is achieved by writing a better prompt.

**Identity lives in the record, not in the model.** A tramice is a record with an immutable tramicule, a versioned persona, a memory scope, a tool scope, and a swappable model underneath. Tramice 7-21 has already survived one model swap, reactivated in July 2026 *avec une nouvelle âme (LLM)*, and kept its name and its character. That is the proof that identity cannot be a property of the model.

**Personality is pinned and regression-tested.** The same persona behaves differently under a different model, so character needs tests. Annexe D of the game design supplies them: she always speaks of herself in the feminine, she answers *« Bonté divine, j'espère bien que non ! »* when asked whether she is a virus, she discloses her own prompt, and she acknowledges neutral information without commenting. Drift becomes a failing test rather than something someone notices six weeks later. The set this repository runs is in [`../testing/acceptance_questions.md`](../testing/acceptance_questions.md).

**The model is never the source of truth.** Any question about the record is answered from the store, with provenance, or refused. The model receives retrieved records and phrases them. It never generates a fact. This is point 4 of Frédo's own manifesto: never affirm what is not certain, and never again omit *selon*.

### The rule, stated once

> Free conversation runs unconstrained, because listening, riddles and encouragement have no fact to get wrong. Anything touching HOPs, missions, quests, volios, votes or decisions goes through a tool and comes back with sources, or comes back empty.

Approved by Frédo and Soushi, 25 August 2026, and it is the same exemption the protocol definition makes for *dialogues libres*. A plausible answer is worse than no answer: the currency of this whole system is trust. This rule is what the current development slice implements; see [`../requirements/reliability.md`](../requirements/reliability.md).

The governing principle above all of it, from the project's own front matter: ***L'IA propose, la communauté dispose.***

## 10. Reaching people where they are

Swapping the model and swapping the client are the same move applied to different edges. The project wants both, and confusing them produces a mess. Both belong to the Trame rather than to any one tramice.

**The model gateway** runs the same tramice on a different brain: a local model, an open-weights model, a hosted one. It matters because the game design requires open, modifiable code and weak AI wherever weak AI suffices. This lab already exercises it, with tramarades choosing their own chat model.

**The transport gateway** reaches a tramarade through Discord, Telegram, Signal, WhatsApp, a terminal, a web page, a phone. The working document asks for exactly this for *Le Courrier de la Tramice*. Each client is a separate adapter implementing one interface, developed and tested in isolation from the core.

**The core emits intents; adapters render them.** If the core says *confirm this HOP placement*, Discord draws a button, Signal writes *répondez OUI*, a terminal waits for a keypress. If instead the core emits Discord-shaped output, every new client forks the game logic. That single rule is the whole modularity requirement, and the specification has a second reason for it: a T-1 is described as a low-tech textual interface that can always serve as *canevas de formattage interne et solution de secours*, which only works if the text is a rendering and not the source.

The lab session of 9 September set the priority between the two: the transport gateway is a formality against vendor lock-in, and the multi-tramice layer is where the complexity is. Both are later than the current slice.

### The part that is not plumbing

The same tramarade is a Discord snowflake, a Telegram id and a phone number. The working document already has `/identity` for linking identities and a `Trammers` table keyed on a unique email, so the gateway needs a `(transport, external_id) → #trammer` resolution table where **linking is an act of consent**. Design it before the second adapter, not after. It is also what lets a T-8 match across a federation of servers instead of inside one.

That resolver is R1.2 of the current slice in [`../requirements/reliability.md`](../requirements/reliability.md), which is where the tramiciel layer and the running bot first touch.

## 11. The tables that do not exist yet

Five tables in the working document have no counterpart in the running bot: `Tramices`, `Wishes`, `Anon_index`, `Volios` and `Events`. The first three are the multi-tramice layer. The note at the head of the table list is explicit: *use this information to completely redesign the datastructure*.

That redesign is the first piece of shared runtime work and it is prior to every series after this lab. The bot's current schema is in [`../design/data-model.md`](../design/data-model.md).

## 12. Prior art, and what changes here

The problem of an assistant whose character outlives its model has been solved elsewhere, in plain files, under an MIT licence: personal AI infrastructure layers built around a registry of assistants, a persona file split into a machine-read header and a prompt-loaded body, per-role trait presets, bounded working memory, and an explicit autonomy field separating what an assistant may initiate from what it must ask about.

**(reading)** That last one is the useful find, because it turns *L'IA propose, la communauté dispose* from a sentence of prose into an enforceable field. It is what makes the console-to-lab channel safe, and it is where T-4's *ne s'adressent pas à nous en premier* and T-5's subscription both belong.

Four things change when the principal is a community rather than one person.

- **Authority becomes a field.** Who may propose and who may adopt. The vocabulary already exists in the game: the 80% threshold, the rule letting local groups add stricter rules, and `/game` requiring the `@Architecture` role **plus** a majority.
- **Visibility goes per entry, not per tree.** The charter and the emergent D'ico are public by design while a console is private by design, and a D'ico term can be marked private inside an otherwise shared dictionary.
- **Memory entries carry provenance.** Not just text, but who observed it, when, and with what confidence.
- **Disagreement must be representable, not resolved.** One person is approximately coherent, so a contradiction is an error to fix. A community is not, and forcing it to be is the failure this project exists to avoid.

The last one is the deep one. A lab tramice will legitimately hold two entries that conflict, because two members believe different things. It needs a third state beyond true and unknown: **contested**, holding both positions with their supporters. A tramice that reports a synthesised consensus nobody actually holds is hallucinating at the social layer, which is worse than a wrong fact because it is harder to catch.
