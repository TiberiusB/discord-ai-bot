# Avis de journalisation — Tramice721

> Modèle à publier dans un salon visible de votre serveur Discord avant d'activer
> la tramice en production. Adaptez les noms de salons selon votre configuration.

---

## Message suggéré (français)

**Tramice721 — transparence sur la mémoire et l'IA**

Bonjour à toutes et à tous,

**Tramice721** est l'assistante IA du Laboratoire tramiciel n°721. Pour vous
aider (résumés, mise en relation, questions sur le jeu), elle peut **enregistrer
localement** les messages des salons où elle est autorisée à intervenir.

**Ce qui est enregistré**
- Messages des salons listés dans `channels.log_allowlist` (ou l'allowlist
  historique) de la configuration
- Messages privés (DM) avec Tramice721, pour la mémoire de votre tramice personnelle

**Ce qui n'est pas partagé publiquement**
- Les DM ne sont pas inclus dans les résumés publics du serveur
- Les confidences que vous partagez en privé ne sont pas diffusées aux autres

**Vos droits**
- Commande **`/forgetme`** : supprime vos messages stockés, votre profil (volio),
  vos fils de conversation avec l'IA et vos fragments dans l'index de recherche
- Les données restent sur le serveur qui héberge le bot (local-first), pas chez
  un fournisseur cloud tiers pour le LLM

**Canal(x) concerné(s)** : _[à compléter — ex. #tramice-lab, #general-playtest]_

Des questions ? Mentionnez un admin ou écrivez à Tramice721 en DM.

---

## Notes pour les opérateurs

1. Renseignez `channels.log_allowlist` dans [`config.yaml`](../config.yaml) avec
   les IDs numériques des salons dont les messages doivent être journalisés.
2. Renseignez `channels.interact_allowlist` pour les salons où le bot peut
   répondre (`!ai`, `@mention`, `/ask`). Un salon peut être journalisé sans
   interaction (ex. liste ToDo : log seulement).
3. Ne mettez **pas** de salons sensibles (modération, staff, confidences) dans
   ces listes.
4. Conservez `log_mode: allowlist` pour un déploiement contrôlé (< 100 membres).
5. Testez `/forgetme` sur un compte de test avant d'annoncer le bot au public.
