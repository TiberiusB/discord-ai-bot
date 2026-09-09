# Open questions

> **Sources.** Frédo's *Questions ouvertes* list in the working document, tab *Work in progress*, marked there *à mettre en évidence quelque part dans le labo tramiciel*; the third-pass reading of 26 August 2026 and its own closing questions; Tibi's question recorded in the same document.

This page exists because Frédo asked for these to be visible somewhere in the lab, and a repository everyone can read is somewhere. Nothing here is answered by writing it down. Each question carries **who asked it** and **whose answer it is**, because those are not always the same person, and because the working document mixes questions in Frédo's own French voice with questions folded in from the development side in English. Where a question originated on our side it says so.

## Protocol

### Q01 · What exactly is the Fabric, and who runs it?

If the Trame is the runtime rather than any tramice, then it is a thing with maintainers, a release, and a place it lives. Is the Discord lab a temporary scaffold that gets retired once the Fabric stands on its own, or does it stay as one lab among many?

The specification's own note pushes toward the first reading: the register, persona loading, memory and tool scoping, and retrieval-or-refuse *should be written as Fabric core rather than lab code*. That says what belongs in the Fabric. It does not say who maintains it or where it lives.

**Asked from** the development side, carried in the working document. **Answer belongs to** Frédo and Tibi together, since it decides what this repository becomes.

---

### Q02 · How do the universal game variables stay synchronised?

> Comment synchroniser les variables universelles du jeu (budget, activité, majorité, ~ 12 en tout) entre les tramices ? Quelle est la formule pour éviter (ou sinon : résoudre) des divergences entre les versions tenues pour vraies par les différentes tramices ?

This is the question that decides whether the ecosystem is a federation or a fleet.

**(reading)** Our answer, offered rather than assumed: the variables are not replicated state, they are quantities **derived from a shared log of events**. Two tramices that read the same booklet chain compute the same budget, and a divergence is an alarm rather than a merge conflict.

**Asked by** Frédo. **Answer belongs to** Frédo, with the implementation consequence ours.

---

### Q03 · What governs tramice-to-tramice communication?

The message shape is settled: a volio, flagged `is_systemic?`, carrying a `scope` of `lab`, `global`, `direct` or `network`. What that scope field *does* at a border has no algorithm behind it, and the trust question underneath is untouched: **what is a tramice entitled to believe from another tramice it did not build?**

Frédo's founding letter names the first two things that should cross a lab boundary: wishes the local tramarades could not answer, and new lexicon entries.

**(reading)** Our position on trust: signed, fetchable artifacts with a validity window, never live calls, and no tramice trusted because of who sent the message. The transport is the easy half and is partly a platform accident, since Discord blocks bot-to-bot messaging and webhooks route around it.

**Asked by** Frédo, who records that *le Protocole tramiciel est en cours de rédaction*. **Answer belongs to** Frédo. It has the widest blast radius of anything on this page.

---

### Q04 · Can a tramice be retired, and who decides?

> Cycle de vie des tramices ~ Une tramice peut-elle être « retirée » ? Selon quelles modalités ? Une T-0 vérifie l'attribution, mais qui décide de la fin de vie d'une tramice ? (ex. si plus personne ne l'utilise, si elle est obsolète, si elle est source de problèmes)

`date_retired` is already a field in the `Tramices` table, so the schema assumes retirement exists. The process does not.

**Asked by** Frédo. **Answer belongs to** Frédo.

---

### Q05 · Who proposes a new tramice?

> Qui décide qu'une nouvelle tramice (ex: une T-9 en permaculture) doit être créée ? Qui vérifie son expertise ? Le processus de création et de vérification des tramices (la partie après le tiret) est mentionné mais pas détaillé. Sans ça, l'écosystème risque de devenir anarchique ou capturé par une minorité.

**Half of this is now answered.** The T-9 entry states that expertise *is* verified, over time and on a free basis: **attributed and revocable**. So the correction mechanism is the T-6 tribunal, not a gate at creation.

The other half stands. A T-0 checks the number, the non-duplication and the clarity of the role, all properties of the description. Nothing says who may put a proposal in front of it.

**Asked by** Tibi. **Answer belongs to** Frédo, and the warning is Tibi's: without it, capture by a minority.

---

### Q06 · What happens when a console is lost or compromised?

> Le système d'ephemeral_id repose sur la confiance dans la T-1 du / de la tramarade. Que se passe-t-il si une T-1 est compromise ou si un.e tramarade perd l'accès à sa clé ? Proposition : prévoir un mécanisme de récupération d'urgence via une T-6, avec vérification d'identité par un jury. Vérifier d'abord via le parrainage.

Frédo has already proposed the answer: emergency recovery through a T-6 with jury identity verification, checking the sponsor chain first.

The related consequence, raised from our side: a lost T-1 leaves its tramarade's published wishes in the WOOM, still matchable and no longer attributable to anyone who can act on them. So the key needs an escrow the tramarade controls, or wishes need an expiry, or both. Recovery and expiry are different mechanisms and both may be wanted.

**Asked by** Frédo, with the expiry half from our side. **Answer belongs to** Frédo. This one is close to decided.

---

### Q07 · Is *tramicien / tramicienne* a good idea?

> J'ai joué à inventer le terme de *tramicien* / *tramicienne* pour désigner les personnes qui œuvrent à mettre au point les tramices : est-ce une bonne idée ? Est-ce que cela ne crée pas une démarcation inutile, voire néfaste entre les tramarades ?

A vocabulary question with a governance edge, which is why it sits here rather than in the [lexicon](lexicon.md).

**Asked by** Frédo, and signed by him in the document. **Answer belongs to** the tramarades.

---

### Q08 · Should this documentation be in French?

These pages are in English because the technical work happens in English and the repository's other documentation is in English. Every game term keeps its French form and is defined in both languages in the [lexicon](lexicon.md).

If Frédo would rather think about this in French, it gets rewritten.

**Asked from** the development side. **Answer belongs to** Frédo.

---

## Beyond the protocol

Frédo's other open questions from the same list. They shape the game rather than the network, but they reach the code and none of them is decided.

### Q09 · Is the booklet ceiling right?

> Nous avons un plafond commun pour les Carnets de reconnaissance, 99 999.99 HOPs. Est-ce suffisant ? Ou alors trop ?? Aussi, devons-nous en avoir un quant à l'appui que peut recevoir une Quête, une Mission ou une Entreprise ? Quelle serait la formule, comment serait fait ce calcul ? Sur quels critères se baserait-il ?

A related count is open from the third pass and should be settled before anything encodes it: the recognition booklets page says **64** slips, two per page; Annexe B says **60** for the Tramice edition.

### Q10 · How is the *indice de mutualité* computed?

> Comment calculer l'indice de mutualité ? [...] peut-être devrions-nous seulement utiliser cet indice pour détecter les appuis suspects [...] on peut se demander si quelqu'un ne pourrait pas appuyer ses propres missions ~ mais peut-être pas à 100 % ?? Fixer un pourcentage maximum ?

Because the formula is undecided, a tramice asked for the current value **declines**. That decline is a test case in [`../testing/acceptance_questions.md`](../testing/acceptance_questions.md), and it stays a decline until this question closes.

### Q11 · How far outside the Guild do we look?

> À quel point voulons-nous « rester entre tramarades » ? Voulons-nous au contraire lister du grand monde tout ce qu'il est possible de lister ? Ou sinon, selon quels critères ?

### Q12 · What is the policy on enterprises?

> Qu'est-ce que cela change qu'une mission fasse partie d'une entreprise ou pas ? Est-ce qu'on veut que n'importe qui puisse lancer une mission [...] ou seulement des entreprises reconnues ? Reconnues comment, d'ailleurs ? ~ Et si la notion d'entreprise était remplacée par celle d'équipe, plus émergente ?

This one has schema consequences: `enterprise` is an `actor_type` on volios and has its own table.

### Q13 · Should screen time be limited?

> Faut-il songer à contingenter le temps d'écran ? Celui-ci est-il un droit inaliénable et sans limite, ou y a-t-il des limites psychologiques et écologiques qu'il serait dangereux de dépasser ?

Frédo's own leaning is toward alerting rather than rationing, for personal health or for necessary energy rationing.

### Q14 · Which laboratory comes after this one?

7xx is general on purpose, and the second lab is what proves the abstraction is not secretly shaped like the first. A research lab, a finance lab and a marketing lab would each stress it differently.

**Addressed to** Tibi in the working document.

---

## Resolved since the third pass

Kept so that a reader who saw the earlier reading knows why it changed.

| Question | Resolution |
|---|---|
| Do the 2, 3, 5 and 6 series have roles, or are they reserved? | All assigned. See [the catalogue](series.md) |
| Does the T-0 attest without blocking? | Yes. It notifies, a T-6 convenes, the tramarades vote at 80% for major changes |
| Does a lab keep its own D'ico permanently? | Yes, and its own lexicon with it |
| Is the 4 series the interpretive layer over the 0 series? | No. T-0 holds the present, T-4 archives it, T-5 narrates it |
| **Who owns the tramice register?** | **The specification settles it: a T-0 verifies and locks the tramicule, and a T-0 holds the register. The T-8s mirror the list of active tramices. An earlier reading on our side had a T-8 doing the verification, which would have split the record across three series; it does not.** |
| Is a T-9's expertise checked? | Yes, but *over time and on a free basis: attributed and revocable*. The gate is not at creation; the correction is the T-6 tribunal. Who may *propose* one is still [Q05](#q05--who-proposes-a-new-tramice) |
