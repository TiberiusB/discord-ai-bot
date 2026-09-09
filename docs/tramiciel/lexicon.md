# The lexicon

> **Sources.** Frédo's bilingual equivalence table in the working document, tab *Work in progress*, reproduced verbatim below; his abbreviations list in the same tab; the volios directory of 25 August 2026 for the definition of *volio*; the series specification for the tramice vocabulary; *Un jeu pour système* for the game terms.

Frédo asked for this page. The working document carries it as a task: *Créer un lexique des termes tramiciels, comme tramarade, tramice, tramer, le terme tramiciel lui-même, etc. Y adjoindre les expressions spécifiques au Jeu [...] Both in English and French.*

It exists for a second reason he states separately, and it is a requirement rather than a preference:

> Idéalement, j'aimerais que le vocabulaire utilisé pour décrire le système aux usagers (le jeu aux joueurs, la Trame aux tramarades) soit le même, ou du moins reconnaissable, dans le code du robot. Cela par souci de transparence, que des tramarades sans notion de programmation puissent comprendre le code.

So this page is not a courtesy for readers of the documentation. It is the naming authority for the code. A symbol in the bot that means *appui* should be called `appui` or `support`, consistently, and not `influence`.

## Frédo's equivalence table

Reproduced as written, English on the left, French on the right.

| English | French |
|---|---|
| tramice | tramice |
| tramicial | tramiciel·le |
| tramician | tramicien·ne |
| tramice number | tramicule |
| trammer | tramarade |
| The Fabric of Wishes | La Trame Étoilée |
| the Fabric | la Trame |
| to weave, tramming | tramer, tramage |
| The Trammers Guild | La Guilde des Tramarades |
| HOPs of support | HOPs d'appui |
| booklet | carnet |
| Booklet of Recognition | Carnet de Reconnaissance |
| Mission Booklet | Carnet de Mission |
| placement period | période de placements |
| allocation of universal modicum (AUM) | allocation universelle modique (AUM) |
| Mondo panel | fenêtre Mondo |
| Quest | Quête |
| labo tramiciel | tramicial lab |
| promise of convivial usage | promesse d'utilisation conviviale |

Note the adjective: **tramicial** in English, **tramiciel** in French. The English spelling is Frédo's own and is not a misspelling of the French one.

## The people

**tramarade** · *trammer* — A member of the network. The French is the primary form and French strings always use it; English documentation uses either. It is a portmanteau of *tramer* and *camarade*.

**tramicien·ne** · *tramician* — A person who works on building the tramices themselves. Frédo flags his own coinage as an open question: *est-ce que cela ne crée pas une démarcation inutile, voire néfaste entre les tramarades ?* See [question 07](open-questions.md).

**@Architecture** — The lab role required to change the game's design. Any tramarade wanting to change the design relative to the founding proposal must hold it, and changing a universal game parameter requires the role **and** a majority of tramarades.

**@Administration** — The lab role for configuration, model selection and feature flags. Distinct from `@Architecture`, which governs game design rather than operation.

## The things

**tramice** — An entity of the Trame. Feminine in French, and she refers to herself in the feminine. Eleven series, described in [the catalogue](series.md).

**tramicule** · *tramice number* — A tramice's unique identifier: series digits, a hyphen, then a free suffix. `Tramice 7-21` is canonical; `Tramice721` is accepted shorthand.

**la Trame** · *the Fabric* — The runtime the whole ecosystem runs on. Not a tramice.

**La Trame Étoilée** · *The Fabric of Wishes* — The game itself, subtitled *Joignez la Guilde des Tramarades !*

**La Guilde des Tramarades** · *The Trammers Guild* — The community the game constitutes.

**labo** · *lab* — A numbered working group with its own T-7, its own lexicon and its own D'ico. This repository serves *Labo tramiciel n°721*.

**volio** — *Liste de souhaits concrets (personnels ou collectifs) annoncée dans nos réseaux afin d'y informer l'intelligence collective et l'attentive bienveillance.* In English: *list of concrete (personal or collective) wishes announced in our networks to inform collective intelligence and attentive goodwill.*

Everything that can hold an intention has one: tramarades, tramices, teams, events, missions, quests, enterprises, ideas, D'ico entries, places and labs. The volio is also the network's message format; see [the protocol](protocol.md#1-the-volio-is-the-wire-format).

**écho** · *echo* — A wish in the Trame that answers one of yours, notified back to you at the frequency you chose. A T-1 keeps them; `/echoes` lists the unread ones.

**D'ico** — The illustrated, multilingual, emergent glossary. Spelled with the apostrophe because the illustrations are round *ico*ns adopted by tramarades to stand for concepts. It exists at three levels: personal on a T-1, lab on a T-7, and emergent on the T-8s, the last rising from all the others minus terms marked private. Tended by all tramarades, like the Wiktionary.

**WOOM** — *Wish-Oriented Oracular Memory.* The emergent database of anonymised current wishes plus the emergent D'ico, mirrored across the T-8s. The mnemonic: the double O in wOOm is an 8 lying down.

**Mondo** · *Mondo panel* / *fenêtre Mondo* — The window onto the ecosystem, with a *perso* mode and a *cosmo* mode.

**À-propos** — The dialogue window of a personal console.

**salon** — A Discord channel. Used throughout as the counterpart of *DM*, and the two are the surfaces the acceptance questions distinguish.

## The economy

**HOP** — *Heure d'Ouvrage par une Personne*: an exchange unit based on human time. Two decimal places.

**appui** · *support* — What a tramarade places on a mission, a quest or an enterprise, denominated in HOPs. **HOPs d'appui** · *HOPs of support*.

**budget d'appui** — The weekly allowance of HOPs a tramarade may place. Reset weekly.

**période de placements** · *placement period* — The window during which appui may be placed.

**carnet** · *booklet* — The ledger holding exchange value. **Carnet de Reconnaissance** · *Booklet of Recognition*, individual or tied to a mission. **Carnet de Mission** · *Mission Booklet*. The shared ceiling is 99 999,99 HOPs, and whether that is the right number is one of Frédo's open questions.

**AUM** — *allocation universelle modique* · *allocation of universal modicum*. Reset to its base amount every Sunday at midnight; each tramarade uses it during the week or does not.

**mission** — Work deposited by an enterprise, detailing its needs in HOPs and resources. A mission is an intention, so it is announced in the network as a volio.

**quête** · *Quest* — Work recognised after the fact, the following week.

**entreprise** · *enterprise* — An organisation on the network. Whether the concept should survive at all, or be replaced by the more emergent notion of a team, is one of Frédo's open questions.

**indice de mutualité** — A proposed measure whose formula is undecided. Because it is undecided, a tramice asked for its current value declines rather than computing one; that decline is a test case in [`../testing/acceptance_questions.md`](../testing/acceptance_questions.md).

**promesse d'utilisation conviviale** · *promise of convivial usage* — The undertaking a newcomer makes before any action on the server is permitted. A gate, not a formality.

## Renamings on record

The working document records four, and code and documentation should follow them.

| Was | Is | Where recorded |
|---|---|---|
| `budget d'influence` | `budget d'appui` | Task list, and throughout the rewritten persona text |
| `investissement`, *investir* | `appui`, *appuyer* | The persona paragraph, rewritten. HOPs of appui do not pay dividends; they support missions and enterprises |
| `trammer` in French strings | `tramarade` | Abbreviations list: *En français, 'trammer' se dit 'tramarade' et 'support' se traduit par 'appui'* |
| `/signal`, `/son` | `/report`, `/sound` | *We decided that all commands will be in English* |

The current state of the command surface, and which names are agreed, is in [`../design/command_inventory.md`](../design/command_inventory.md).

## What this page is not

It is not the D'ico. The D'ico is emergent, illustrated, tended by every tramarade, and it lives in the running system across three levels. This page is the stable technical vocabulary of the project, written down so that documentation, code and conversation use the same words. Frédo's task also asks for the terms to populate the `Dico` table; that is a data task in the bot, and this page is where its initial content can be read off.
