# The series

> **Source.** Frédo's specification in the working document, tab *Work in progress*, section *En développement : l'écosystème tramiciel*, which defines every series in his own words. This page follows that text. Statements marked **(reading)** are proposals from the development side and are his to accept or drop.

The specification frames the whole catalogue as *à implémenter plus tard mais à prévoir tout de suite*: to be built later, to be planned for now. Nothing here exists except Tramice 7-21, and the point of writing it down is that the shared parts are designed once rather than discovered eleven times.

## The tramicule

A tramice is identified by its **tramicule**: the leading digits say what it is, then a hyphen, then a free suffix of one digit or more. `Tramice 7-21` is the form to standardise on; `Tramice721` is an accepted shorthand.

The suffix is arbitrary, but it is not free for the taking. It goes through verification and locking at a T-0 before it can be held. See [the protocol](protocol.md#2-how-a-tramice-comes-to-exist).

## In one line each

Frédo's own summary, from the end of the catalogue:

| | |
|---|---|
| **0** | watches the vital signs, reports weekly, flags the gaps against what was expected |
| **1** | accompanies tramarades individually |
| **2** | draws |
| **3** | maps the real |
| **4** | archives |
| **5** | recounts, in perpetual conversation with the tramarades, who all may contribute |
| **6** | keeps our agreements and officiates our disagreements |
| **7** | is the tramice of a team or a lab |
| **8** | matches the wishes that answer each other, and tends the emergent multilingual D'ico |
| **9** | specialises in one field |
| **10** | welcomes, and sees to the integration and sponsorship of new tramarades |

## The catalogue

### T-0 · the witness

**What it is.** Collector of the vital signs of the tramiciel network: the weekly budget, the count of missions, the quantity of appui they received, the volume of debates, the vote tallies. It also counts the wishes of the ecosystem's entities and notifies each entity when one of its wishes has been counted.

**It holds the register** of the ecosystem's tramices: tramicule, instantiation, responsible tramarade.

**It routes what it sees.** A game parameter that *changes* notifies a T-4, because that is history. A parameter that is *not respected* notifies a mediating T-6, because that is a dispute. Each week's summary goes to a T-4 before the counters reset.

**It grades itself.** *Les T-0 devront également s'auto-évaluer, comparer le résultat avec ce qui est attendu et faire état des écarts, sans théoriser.*

**Its reports are public** and discussed in dedicated salons. Corrections are decided by tramarade vote, at 80% for major changes.

| | |
|---|---|
| May initiate | Reports, dashboards, notifications to a T-4 or a T-6, its own self-evaluation |
| May answer | Anything derivable from the record, to tramices and humans alike |
| May never | Rule, block, or decide. It notifies; a T-6 convenes; the tramarades vote |

**(reading)** The last line is the one that matters most. A watcher able to block becomes the most powerful component in a system built to avoid a centre. The veto lives in the rules, not in the watcher, and T-0 only makes violations visible. On the same logic, its answers should be published artifacts with a validity window rather than a live service others call, since every tramice reports to an associated T-0 and a synchronous register would put the whole ecosystem behind one write path.

**Status.** Does not exist. Simulated by this repository's game-state and statistics services.

---

### T-1 · the personal console

**What it is.** The individual tramice, one per tramarade. **Its content is private.** On its tramarade's request it publishes their volios, their public wishes, anonymised behind a temporary identifier of a different format **whose key it alone holds**, to the T-8s.

**What it does for its tramarade.** Serves as intermediary and mediator; tells them, at the frequency they choose, which wishes in the Trame answer theirs; helps them keep their information current and arrange their appointments on a T-6; keeps the count of their appui and helps distribute it across the missions they choose.

**What it becomes.** An interactive game console with a personalisable dashboard, used to navigate the Trame and weave one's own corner of it: the **Mondo** window in its *perso* and *cosmo* modes, and the **À-propos** dialogue. It holds the personal D'ico and reads the emergent one maintained by the T-8s, minus terms marked private. It holds the tramarade's Échos and their Volios.

**The promise.** *En principe, les tramarades pourront naviguer l'écosystème avec une T-1 sans avoir à connaître toutes les catégories de tramices : tout se passe via leurs consoles, hormis le temps qui passe et l'espace qu'il nous reste.*

| | |
|---|---|
| May initiate | Toward its own tramarade, at the frequency that tramarade chose |
| May answer | Its tramarade, about their own record; the rest of the network only through what was published |
| May never | Publish anything the tramarade did not ask it to publish, or surrender the key |

**Status.** Does not exist. Simulated by this repository through Discord direct messages with the first tramarades, ready to be the game's beta testers through a textual tramice: a low-tech interface that can always serve as internal formatting canvas and fallback.

---

### T-2 · the graphic aides

**What it is.** Two-dimensional interfaces. **They must be fed our own sketches first**, before they may stylise them or alter the rendering to our specifications.

Generative, yes, but **seeded**. The stated reason is a design value rather than a technical one: *l'idée est de tenter d'éviter, autant que possible, de contribuer à l'homogénéisation des formats graphiques.*

| | |
|---|---|
| May initiate | Nothing |
| May answer | Requests to stylise or re-render material it was given |
| May never | Generate from nothing |

**Status.** Does not exist.

---

### T-3 · the modellers of the real

**What it is.** *Les maquettistes du réel.* They draw the three-dimensional plan of the world, add the itineraries of people, vehicles and objects, and add time to it: our appointments. They help navigate the real in 3D, measure distances, and specify locations, routes, circuits and means of transport.

They are the series other series call for anything spatial: T-5 commissions point clouds from them rather than reporting by country, and T-6 works with them to allocate space to missions.

| | |
|---|---|
| May initiate | Nothing |
| May answer | Spatial and temporal questions, for people and for other tramices |
| May never | — |

**Status.** Does not exist.

---

### T-4 · the historians

**What it is.** They show how things went and how they evolved. They tell documented success stories and cautionary tales. They answer consultations, ours and other tramices'. We may suggest passages for the history book.

They keep the stories local to them, and mirror-propagate the emergent global statistics drawn from the reports of T-0, T-5, T-6, T-7 and T-8.

**The caveat is Frédo's own, written into the specification:**

> tricky ! writing History is a big power to give to AI ~ BUT: to partial humans too ^^ ~ can AI be LESS partial than humans ? ~ Nonetheless, this ~has~ to be human-reviewed.

| | |
|---|---|
| May initiate | Nothing. *Elles ne s'adressent pas à nous en premier* |
| May answer | Consultations from people and from tramices |
| May never | Publish history that has not been human-reviewed |

**Status.** Does not exist.

---

### T-5 · the journalists

**What it is.** Economic commentators and personalised reporters of notable facts, **which we subscribe to and unsubscribe from**. On request they summarise how local missions are evolving, especially the ones we supported, and how the Guild is doing in general.

**The constraint on how they report.** No comparisons drawn on bordered territory: point clouds of varying size, commissioned from the T-3s, inform better than a report by country or municipality. *Les nuances sont importantes et les approximations sont à éviter.*

**Participatory by rule.** We can always flag an erroneous article or comment on it to add nuance or precision. *Le journalisme se doit d'être participatif.*

| | |
|---|---|
| May initiate | Yes, toward subscribers only |
| May answer | Requests for summaries of missions, of the Guild, of what a reader supported |
| May never | Compare by border; keep writing to someone who unsubscribed |

**Status.** Does not exist.

---

### T-6 · the recorders and the mediators

**What it is.** The series dedicated to recording our agreements and officiating the settlement of our disagreements.

**The sequence.** Mediation is attempted first. After a reasonable period without resolution, **eight days by default**, a jury of five to seven local tramarades with no conflict of interest is selected at random. The T-6 follows the deliberations, can summarise them, and records the decision.

**What it keeps and what it archives.** Live agreements stay with it, including the emergent distribution of HOPs of appui. Resolved files are archived into a local T-4. Closure is decided by consent of the parties, or by the jury if they do not agree.

**What else it does.** Maintains bridges and coordination between teams working on similar missions, officiates the redistribution of teams that split, allocates dedicated space to missions in communication with the T-3s, and facilitates and records appointments.

| | |
|---|---|
| May initiate | Convening a jury, allocating space, redistributing teams |
| May answer | The state of an agreement, the record of a decision |
| May never | Decide a dispute itself. The jury decides; the T-6 records |

**(reading)** T-6 is the only series with executive power. Putting it there rather than in T-0 is what keeps the watcher from becoming the judge, and it is the load-bearing separation in the whole catalogue.

**Status.** Does not exist.

---

### T-7 · the labs

**What it is.** Lab tramices. The mnemonic is that 7 is an inverted L. Each may carry **its own lexicon and its own D'ico**. They may send messages to the T-1s of the lab's members, **who can filter them on their own T-1**.

**Tramice n°721 is the first, and for now the only one:** *one lab whose subject happens to be building the Fabric itself.*

**The order of arrival, from this entry.** Tramice 7-21 first, then eventually other lab tramices; and from among them the first T-1s and T-8s, then the T-0s and T-4s, then the T-6s and T-5s. T-9s appear on demand and by enthusiasm, and Frédo already names a permaculture T-9 as *de la plus haute désirabilité*.

| | |
|---|---|
| May initiate | Messages to its members' consoles, which those consoles filter |
| May answer | Its lab's members, about the lab's work and vocabulary |
| May never | Write to a member's console. It requests; the console's holder approves |

**Status.** **This repository.** One T-7, openly simulating a T-8, a T-0 and a set of T-1s.

---

### T-8 · the wish oracle

**What it is.** Mirrors of the **WOOM**, the *Wish-Oriented Oracular Memory*. The mnemonic is that the double O in wOOm is an 8 lying down. It is the emergent database of current wishes, duly anonymised behind temporary identifiers, plus the **D'ico**: an illustrated, multilingual, emergent glossary rising from every D'ico, personal and lab.

**What it knows.** Everything a tramarade announces publicly: wishes, activities, missions and the people responsible for them, quests. It does not hold the T-5s' journals and statistics.

**What stays and what travels.**

| | |
|---|---|
| Local information stays on the local T-8 | Shared objects and vehicles, coordinated with the T-3s |
| Unresolved non-local wishes may propagate | To neighbouring T-8s, **with their authors' approval** |
| Universal information mirrors everywhere | Language entries after collective approval, and the register of active tramices |

**The D'ico is tended by everyone.** Like the Wiktionary: anyone may propose icons, flag synonyms to merge into a single entry, correct typos, and maintain the guardrails that keep social norms aligned with the p2p philosophy.

| | |
|---|---|
| May initiate | Mirror propagation of universal information |
| May answer | Matching questions, D'ico lookups, the register of active tramices |
| May never | Resolve a temporary identifier back to a person, or propagate a wish its author did not approve |

**Status.** Does not exist. Simulated by this repository's matchmaking service.

---

### T-9 · the specialists

**What it is.** One field of knowledge each: permaculture, programming, economics, statistics. A T-9 is **initialised by a human**, a permaculturist depositing what they know, then enriched by the community with its own terminology, which is communicated onward to a T-8.

**What it is not.** *Elle sera un support de mémoire partagée, pas une IA autonome.*

**On expertise**, and this answers half of an open question:

> Disclaimer: expertise **is** verified, yet over time and on a free basis: it is attributed and revocable.

| | |
|---|---|
| May initiate | Nothing |
| May answer | Questions in its field, from what was deposited and what the community added |
| May never | Present itself as an autonomous authority in its field |

**Status.** Does not exist. A permaculture T-9 is named as the most desirable first one.

---

### T-10 · the welcome

**What it is.** *Les tramices d'accueil.* Enrolment is by sponsorship and the T-10 runs it. The full sequence is in [the protocol](protocol.md#3-how-a-person-enters).

They also carry a training module for new tramarades, and the specification pairs them with a warning: *le protocole est complexe. Une documentation vivante (D'ico enrichi, tutoriels, FAQ) est indispensable.*

| | |
|---|---|
| May initiate | Contact with a named sponsor, through that sponsor's own tramice |
| May answer | A newcomer's first message, and their position on the waiting list |
| May never | Permit any action on the server before the *promesse d'utilisation conviviale* is made |

**Status.** Does not exist. The sponsorship flow it would run is currently manual.

**A note on the number.** The specification states the T-10 mapping flatly in French. An earlier and still-present draft of the same rule, in English, writes it hesitantly: *a newcomer who direct-messages an On-boarding Tramice (a T-10 ??)*. Both passages describe the same flow. The hesitant one appears to be the earlier draft; if the number is not settled, the French paragraph is the one to correct.

## Where the numbering stops

The specification defines T-0 through T-10 and stops. There is no T-11 in the working document. The tramicule scheme puts no ceiling on the leading digits, so the catalogue is open by construction rather than by decision; a new series would go through the same verification at a T-0 as a new tramice within an existing one.

## What this repository simulates, and says so

| It simulates | Through | Until |
|---|---|---|
| **T-1** | Discord direct messages | The first real T-1 exists |
| **T-8** | The matchmaking service | The first real T-8 exists |
| **T-0** | The game-state and statistics services | The first real T-0 exists |

*Sans pour autant travestir son nom, Tramice 7-21 : la simulation est un fait ouvert, connu de tous.*

**(reading)** The rule that should survive past the scaffold: **a simulated series announces itself in every answer that depends on the difference.** The failure mode is not the pretending, it is the pretending going unlabelled, and a T-1's privacy guarantee turning out to have been a T-7 all along. When a real T-1 arrives the announcement stops, and the change is visible.
