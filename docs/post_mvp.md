# Post-MVP — Tramice721 Discord Bot

> Wishlist outcome after milestones M0–M6 (July 2026).  
> Last updated: 17 July 2026.  
> **What was built** lives in [`implementation_status.md`](implementation_status.md)
> (Post-MVP round + Implemented by layer). Roadmap: [`planning.md`](planning.md).

---

## Outcome

The original post-MVP wishlist is **shipped** and largely **smoke-tested** on the
lab guild (Phase 0). Do not duplicate feature write-ups here — see
[`implementation_status.md`](implementation_status.md).

| Theme | Status | Notes |
|-------|--------|-------|
| Activity traces on `/forgetme` | **Done** | See implementation status → Post-MVP round |
| Member aliases + `/identite` | **Done** | Auto-track + slash link/list |
| Capability scan + agent strategy | **Done** | Daily scan; `get_discord_capabilities` |
| Threads / polls / TTS | **Done** | `/thread`, `/sondage`, `/say` (TTS used live) |
| Discord scheduled events | **Done** | `/event` + `game_week_open`; lab has `MANAGE_EVENTS` |
| Governance escalation DMs | **Done** | Threshold-based admin suggestions only |
| Soundboard list (`/son`) | **Partial** | Lists sounds; playback deferred |
| Admin-curated web RAG | **Done** (related) | `/web-source` + Chroma `web` (same July window) |

---

## Remaining / deferred

Intentional leftovers from the post-MVP notes (also listed under Known gaps in
[`implementation_status.md`](implementation_status.md)):

| Item | Notes |
|------|-------|
| Soundboard **playback** | `/son` lists; no voice-channel play path yet |
| Agent-initiated threads / TTS | Slash commands only; no create-thread/TTS agent tools |
| `@everyone` send helper | Permission tracked in strategy; send path gated off |
| Proactive Échos DMs | Propose-only; opt-in notify in [`planning.md`](planning.md) Phase 3 |
| Identity tools for the agent | `/identite` works; no LangChain wrapper yet |

Day-to-day playtest backlog (slash renames, read-only salons, `/mode`, etc.)
lives in [`current_work.md`](current_work.md).


# New ideas to implement

- Pouvoir interpeller la Tramice par son nom dans les salons publiques, sans @ ni !ai ~ ça marche dans les DMThis requires active monitoring of public channels, which is resource intensive. This could be implemented once we can use a larger computer system host, and perhaps better AI models. This could also be implemented using a small LLM that only monitors the chat and decides if the user talks "about" Tramice or "to" Tramice. 

- Que certaines commandes slash soient visibles pour tous dans les salons, et pas seulement pour leurs auteurs (missions, quêtes, entreprises, événements, volios publics). Voir la liste complete des commandes. 

- Intégrer module léger qui détecte si on parle DE la tramice ou À la tramice (y inclus ses surnoms : tramimi, Mme T, 721, etc.) afin de ne pas consommer trop de ressources

- Ajouter une commande /freq pour changer la fréquence à laquelle Tramice met à jour les Échos pour le/la tramarade qui le demande.

- Tenir compte des pouces par en bas () sur les répliques de Tramice en vue du backtracking tes erreurs (LoRA).

- Donner à Tramimi accès à la météo locale (pour un.e tramarade donné.e).

- application primitives

Create "equipe" primitive along with member, mission, etc. 
Les membres peuvent 