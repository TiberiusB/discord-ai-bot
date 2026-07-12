"""Slash command registration (spec §7.3).

Commands are added per milestone. M1: ``/ask`` (agent) and ``/model`` (admin
model swap). Later milestones extend this module in place.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from bot.handlers import make_request
from bot.observability import audit

log = logging.getLogger("tramice.commands")

PERM_DENIED = "Je n'ai pas la permission pour cette action."


async def _run_agent_interaction(
    bot, interaction: discord.Interaction, content: str, command: str
) -> None:
    """Defer an interaction, route it through the queue, reply via followup."""
    await interaction.response.defer(thinking=True)
    is_dm = interaction.guild is None
    req = make_request(
        guild_id=str(interaction.guild_id) if interaction.guild_id else None,
        channel_id=str(interaction.channel_id),
        user_id=str(interaction.user.id),
        user_name=getattr(interaction.user, "display_name", None),
        is_dm=is_dm,
        content=content,
        trigger="slash",
        command=command,
    )
    req.reply = interaction.followup.send
    accepted = await bot.router.submit(req)
    if not accepted:
        await interaction.followup.send(
            "Je suis un peu débordée — réessaie dans un instant."
        )


def register_commands(bot) -> None:
    tree = bot.tree

    @tree.command(name="ask", description="Poser une question à Tramice721.")
    @app_commands.describe(question="Ta question (facultatif en DM)")
    async def ask(interaction: discord.Interaction, question: str | None = None):
        await _run_agent_interaction(bot, interaction, question or "Bonjour !", "ask")

    @tree.command(
        name="forgetme",
        description="Supprimer tes données stockées (messages et profil).",
    )
    async def forgetme(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        services = bot.services
        if services is None or services.memory is None:
            await interaction.followup.send("La mémoire n'est pas disponible.")
            return
        result = services.memory.forget_user(str(interaction.user.id))
        audit(str(interaction.user.id), "forgetme", result="ok")
        await interaction.followup.send(
            "C'est fait, j'ai effacé tes traces. 🌿\n"
            f"- messages anonymisés : {result.messages_deleted}\n"
            f"- volios supprimés : {result.volios_deleted}\n"
            f"- confidences supprimées : {result.confidences_deleted}\n"
            f"- échos supprimés : {result.echoes_deleted}\n"
            f"- profil supprimé : {'oui' if result.profile_deleted else 'non'}"
        )

    @tree.command(
        name="reindex", description="[Admin] Reconstruire l'index documentaire (RAG)."
    )
    async def reindex(interaction: discord.Interaction):
        if not bot.is_admin(interaction):
            await interaction.response.send_message(PERM_DENIED, ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        services = bot.services
        if services is None or services.knowledge is None:
            await interaction.followup.send("Le service de connaissances n'est pas prêt.")
            return
        try:
            result = await bot.loop.run_in_executor(None, services.knowledge.reindex)
        except Exception as exc:  # noqa: BLE001
            await interaction.followup.send(
                "L'indexation a échoué. Vérifie qu'Ollama tourne et que le modèle "
                f"d'embedding est installé (`ollama pull {bot.settings.embed_model}`).\n"
                f"Détail : {exc}"
            )
            return
        audit(str(interaction.user.id), "reindex", result="ok")
        await interaction.followup.send(
            f"Index reconstruit : {result['documents']} documents, "
            f"{result['chunks']} fragments dans la collection « {result['collection']} ». 📚"
        )

    @tree.command(name="health", description="[Admin] État de santé de la tramice.")
    async def health(interaction: discord.Interaction):
        if not bot.is_admin(interaction):
            await interaction.response.send_message(PERM_DENIED, ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        ollama_ok = await bot.ollama.ping()
        sqlite_ok = bot.settings.app_db_path.exists()
        chroma_ok = bot.settings.chroma_dir.exists()
        jobs = []
        if bot.scheduler is not None:
            for job in bot.scheduler.get_jobs():
                nxt = getattr(job, "next_run_time", None)
                jobs.append(f"  - {job.id}: {nxt}")
        lines = [
            "**État de Tramice721 :**",
            f"- Modèle : `{bot.ollama.model}`",
            f"- Ollama joignable : {'oui ✅' if ollama_ok else 'non ❌'}",
            f"- Base SQLite : {'ok' if sqlite_ok else 'absente'}",
            f"- Index Chroma : {'ok' if chroma_ok else 'absent'}",
            "- Tâches planifiées :",
            *(jobs or ["  (aucune)"]),
        ]
        await interaction.followup.send("\n".join(lines))

    @tree.command(name="model", description="[Admin] Changer le modèle Ollama.")
    @app_commands.describe(name="Nom du modèle Ollama (laisser vide pour lister)")
    async def model(interaction: discord.Interaction, name: str | None = None):
        if not bot.is_admin(interaction):
            await interaction.response.send_message(PERM_DENIED, ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        available = await bot.ollama.list_models()
        if not name:
            current = bot.ollama.model
            listing = "\n".join(f"- {m}" for m in available) or "(aucun modèle trouvé)"
            await interaction.followup.send(
                f"Modèle actuel : **{current}**\nModèles disponibles :\n{listing}"
            )
            return
        if available and name not in available:
            await interaction.followup.send(
                f"Le modèle `{name}` n'est pas installé. Fais `ollama pull {name}` "
                "d'abord, ou choisis parmi la liste (`/model`)."
            )
            return
        bot.ollama.set_model(name)
        audit(str(interaction.user.id), "model_swap", args={"model": name})
        if getattr(bot, "on_model_changed", None):
            bot.on_model_changed(name)
        await interaction.followup.send(f"Nouvelle âme chargée : **{name}**. 🌱")

    register_m4_commands(bot)
    if bot.settings.get("features.game_simulation", True):
        register_m5_commands(bot)
    log.info(
        "Registered slash commands: /ask, /forgetme, /reindex, /model, /health, "
        "/volio, /mondo, /echoes, /event, /summarize, /normes, /norm-set, "
        "/signalement, /mission, /place, /vote"
    )


def register_m4_commands(bot) -> None:  # noqa: C901 - cohesive command block
    tree = bot.tree
    services = bot.services

    def _svc(name):
        return getattr(services, name, None) if services else None

    # ---- /volio (identity) --------------------------------------------
    @tree.command(name="volio", description="Voir ou enrichir ton volio (profil).")
    @app_commands.describe(
        action="list (défaut) ou add",
        kind="search|interest|talent|offer|request|placement",
        label="Intitulé de l'entrée",
        details="Précisions (facultatif)",
        visibility="private|network|public",
    )
    async def volio(
        interaction: discord.Interaction,
        action: str = "list",
        kind: str | None = None,
        label: str | None = None,
        details: str | None = None,
        visibility: str = "network",
    ):
        identity = _svc("identity")
        if identity is None:
            await interaction.response.send_message("Service indisponible.", ephemeral=True)
            return
        uid = str(interaction.user.id)
        if action == "add":
            if not kind or not label:
                await interaction.response.send_message(
                    "Pour ajouter : précise `kind` et `label`.", ephemeral=True
                )
                return
            try:
                identity.upsert_trammer(uid, display_name=interaction.user.display_name)
                entry = identity.add_volio_entry(uid, kind, label, details, visibility)
            except ValueError as exc:
                await interaction.response.send_message(str(exc), ephemeral=True)
                return
            await interaction.response.send_message(
                f"C'est noté dans ton volio : **{entry.label}** ({entry.kind}). 🌱",
                ephemeral=True,
            )
            return
        entries = identity.list_volio(uid, visibility_filter="all")
        if not entries:
            await interaction.response.send_message(
                "Ton volio est encore vide. Ajoute une entrée avec "
                "`/volio action:add kind:offer label:...`.",
                ephemeral=True,
            )
            return
        body = "\n".join(f"- [{e.kind}] {e.label}"
                         + (f" — {e.details}" if e.details else "") for e in entries)
        await interaction.response.send_message(f"**Ton volio :**\n{body}", ephemeral=True)

    # ---- /mondo (ecosystem) -------------------------------------------
    @tree.command(name="mondo", description="Explorer le Mondo (carte de la Guilde).")
    @app_commands.describe(view="perso ou cosmo (défaut)", kind="type d'entité (facultatif)")
    async def mondo(interaction: discord.Interaction, view: str = "cosmo", kind: str | None = None):
        ecosystem = _svc("ecosystem")
        if ecosystem is None:
            await interaction.response.send_message("Service indisponible.", ephemeral=True)
            return
        from services.ecosystem import MondoFilters

        view = view if view in {"perso", "cosmo"} else "cosmo"
        entities = ecosystem.list_mondo(
            view, str(interaction.user.id) if view == "perso" else None,
            MondoFilters(kind=kind or None, limit=12),
        )
        if not entities:
            await interaction.response.send_message(
                "Le Mondo est encore vide. 🌌", ephemeral=True
            )
            return
        body = "\n".join(
            f"- [{e.kind}] **{e.title}** · phase {e.phase} · {e.hop_requested:.2f} HOP demandés"
            for e in entities
        )
        await interaction.response.send_message(f"**Mondo ({view}) :**\n{body}")

    # ---- /echoes (matchmaking) ----------------------------------------
    @tree.command(name="echoes", description="Voir tes Échos (mises en relation proposées).")
    async def echoes(interaction: discord.Interaction):
        matchmaking = _svc("matchmaking")
        if matchmaking is None:
            await interaction.response.send_message("Service indisponible.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        uid = str(interaction.user.id)
        stored = matchmaking.list_echoes(uid, unread_only=False)
        proposals = matchmaking.find_synergies(uid, limit=5)
        lines: list[str] = []
        if stored:
            lines.append("**Tes Échos :**")
            lines += [f"- {e.summary}" for e in stored]
        if proposals:
            lines.append("\n**Synergies possibles (je propose, tu disposes) :**")
            lines += [
                f"- <@{p.other_id}> — {p.rationale} (score {p.score})" for p in proposals
            ]
        matchmaking.mark_echoes_read(uid)
        await interaction.followup.send(
            "\n".join(lines) if lines else "Pas encore d'écho. Enrichis ton volio pour "
            "que je puisse tisser des liens. 🕸️"
        )

    # ---- /event (coordination) ----------------------------------------
    @tree.command(name="event", description="Proposer ou lister des événements.")
    @app_commands.describe(
        action="propose ou list (défaut)",
        title="Titre de l'événement",
        when="Date/heure (texte libre)",
        location="Lieu",
    )
    async def event(
        interaction: discord.Interaction,
        action: str = "list",
        title: str | None = None,
        when: str | None = None,
        location: str | None = None,
    ):
        coordination = _svc("coordination")
        if coordination is None:
            await interaction.response.send_message("Service indisponible.", ephemeral=True)
            return
        if action == "propose":
            if not title:
                await interaction.response.send_message(
                    "Précise un `title` pour proposer un événement.", ephemeral=True
                )
                return
            from bot.ui import ConfirmView
            from services.coordination import EventSpec

            spec = EventSpec(title=title, starts_at=when, location=location)

            async def _confirm(inter: discord.Interaction):
                created = coordination.propose_event(str(interaction.user.id), spec)
                coordination.confirm_event(created.id)
                audit(str(interaction.user.id), "event_confirm", args={"event": created.id})
                await inter.followup.send(
                    f"Événement confirmé : **{created.title}**. 🎉", ephemeral=False
                )

            view = ConfirmView(interaction.user.id, _confirm)
            await interaction.response.send_message(
                f"Je propose l'événement **{title}**"
                + (f" — {when}" if when else "")
                + (f" @ {location}" if location else "")
                + "\nConfirmes-tu ? (L'IA propose, tu disposes.)",
                view=view,
            )
            return
        events = coordination.list_upcoming_events()
        if not events:
            await interaction.response.send_message("Aucun événement à venir.", ephemeral=True)
            return
        body = "\n".join(
            f"- **{e.title}** · {e.status}" + (f" · {e.starts_at}" if e.starts_at else "")
            for e in events
        )
        await interaction.response.send_message(f"**Événements :**\n{body}")

    # ---- /summarize (governance) --------------------------------------
    @tree.command(name="summarize", description="Résumer l'activité récente du salon.")
    @app_commands.describe(hours="Fenêtre en heures (défaut 24)")
    async def summarize(interaction: discord.Interaction, hours: int = 24):
        governance = _svc("governance")
        if governance is None or interaction.channel_id is None:
            await interaction.response.send_message("Impossible ici.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=max(1, hours))).isoformat()
        until = now.isoformat()
        channel_id = str(interaction.channel_id)
        text, count = governance.collect_channel_text(channel_id, since, until)
        if count == 0:
            await interaction.followup.send("Rien à résumer sur cette période. 🌾")
            return
        summary = await _llm_summarize(bot, text)
        if summary is None:
            summary = governance.summarize_channel(channel_id, since, until).body
        await interaction.followup.send(
            f"**Résumé des {hours} dernières heures ({count} messages) :**\n{summary}"
        )

    # ---- /normes + /norm-set (governance) -----------------------------
    @tree.command(name="normes", description="Afficher les normes sociales en vigueur.")
    async def normes(interaction: discord.Interaction):
        governance = _svc("governance")
        if governance is None:
            await interaction.response.send_message("Service indisponible.", ephemeral=True)
            return
        norms = governance.get_social_norms()
        body = "\n".join(f"- `{k}` : {v}" for k, v in norms.items()) or "(aucune)"
        await interaction.response.send_message(
            f"**Normes sociales (lisibles par tous) :**\n{body}"
        )

    @tree.command(name="norm-set", description="[Admin] Modifier une norme sociale.")
    @app_commands.describe(key="Clé de la norme", value="true ou false")
    async def norm_set(interaction: discord.Interaction, key: str, value: bool):
        if not bot.is_admin(interaction):
            await interaction.response.send_message(PERM_DENIED, ephemeral=True)
            return
        governance = _svc("governance")
        if governance is None:
            await interaction.response.send_message("Service indisponible.", ephemeral=True)
            return
        governance.set_social_norm(str(interaction.user.id), key, value)
        audit(str(interaction.user.id), "norm_set", args={"key": key, "value": value})
        await interaction.response.send_message(
            f"Norme mise à jour : `{key}` = {value}.", ephemeral=True
        )

    # ---- /signalement (governance) ------------------------------------
    @tree.command(name="signalement", description="Faire un signalement gradué (confidentiel).")
    @app_commands.describe(
        level="1=malaise, 2=manquement, 3=danger immédiat",
        description="Description du signalement",
        target="Personne concernée (facultatif)",
    )
    async def signalement(
        interaction: discord.Interaction,
        level: int,
        description: str,
        target: discord.User | None = None,
    ):
        governance = _svc("governance")
        if governance is None:
            await interaction.response.send_message("Service indisponible.", ephemeral=True)
            return
        from services.governance import SignalementSpec

        sig_id = governance.file_signalement(
            str(interaction.user.id),
            SignalementSpec(
                target_id=str(target.id) if target else None,
                level=level,
                description=description,
            ),
        )
        await interaction.response.send_message(
            f"Signalement enregistré (n°{sig_id}, niveau {max(1, min(3, level))}). "
            "Je privilégie d'abord la médiation. 🕊️",
            ephemeral=True,
        )


def register_m5_commands(bot) -> None:  # noqa: C901
    tree = bot.tree
    services = bot.services

    def _svc(name):
        return getattr(services, name, None) if services else None

    # ---- /mission (game) ----------------------------------------------
    @tree.command(name="mission", description="Publier ou lister des Missions (jeu).")
    @app_commands.describe(
        action="publish ou list (défaut)",
        title="Titre de la Mission",
        description="Description / besoins",
        hop="HOP demandés",
        location="Lieu (facultatif)",
    )
    async def mission(
        interaction: discord.Interaction,
        action: str = "list",
        title: str | None = None,
        description: str | None = None,
        hop: float = 0.0,
        location: str | None = None,
    ):
        game = _svc("game")
        ecosystem = _svc("ecosystem")
        if game is None:
            await interaction.response.send_message("Le jeu est désactivé.", ephemeral=True)
            return
        if action == "publish":
            if not title:
                await interaction.response.send_message(
                    "Précise un `title` pour publier une Mission.", ephemeral=True
                )
                return
            from services.game import GameError, MissionSpec

            try:
                entity = game.publish_mission(
                    str(interaction.user.id),
                    MissionSpec(title=title, description=description,
                               hop_requested=hop, location=location),
                )
            except GameError as exc:
                await interaction.response.send_message(str(exc), ephemeral=True)
                return
            await interaction.response.send_message(
                f"Mission publiée : **{entity.title}** ({entity.hop_requested:.2f} HOP "
                f"demandés). Les trammers peuvent investir avec `/place`. 🚀"
            )
            return
        if ecosystem is None:
            await interaction.response.send_message("Service indisponible.", ephemeral=True)
            return
        from services.ecosystem import MondoFilters

        missions = ecosystem.list_mondo("cosmo", None, MondoFilters(kind="mission", limit=15))
        if not missions:
            await interaction.response.send_message("Aucune Mission active.", ephemeral=True)
            return
        body = "\n".join(
            f"- **{e.title}** · {e.hop_allocated:.2f}/{e.hop_requested:.2f} HOP · `{e.id[:8]}`"
            for e in missions
        )
        await interaction.response.send_message(f"**Missions actives :**\n{body}")

    # ---- /place (game) ------------------------------------------------
    @tree.command(name="place", description="Placer ton influence (HOP) sur une Mission.")
    @app_commands.describe(entity="Titre ou identifiant de l'entité", amount="Montant de HOP")
    async def place(interaction: discord.Interaction, entity: str, amount: float):
        game = _svc("game")
        if game is None:
            await interaction.response.send_message("Le jeu est désactivé.", ephemeral=True)
            return
        resolved = _resolve_entity(bot, entity)
        if resolved is None:
            await interaction.response.send_message(
                "Je n'ai pas trouvé cette entité. Vérifie le titre ou l'identifiant "
                "(voir `/mission`).",
                ephemeral=True,
            )
            return
        entity_id, entity_title = resolved
        from bot.ui import ConfirmView
        from services.game import GameError

        async def _confirm(inter: discord.Interaction):
            try:
                placement = game.place_hops(str(interaction.user.id), entity_id, amount)
            except GameError as exc:
                await inter.followup.send(f"Impossible : {exc}", ephemeral=True)
                return
            audit(str(interaction.user.id), "place_hops",
                  args={"entity": entity_id, "amount": amount})
            await inter.followup.send(
                f"Placement confirmé : **{placement.hop_amount:.2f} HOP** sur "
                f"« {entity_title} ». 🌟",
            )

        view = ConfirmView(interaction.user.id, _confirm)
        await interaction.response.send_message(
            f"Tu souhaites placer **{amount:.2f} HOP** sur « {entity_title} ». "
            f"Confirmes-tu ? (Je propose, tu disposes.)",
            view=view,
        )

    # ---- /vote (governance) -------------------------------------------
    @tree.command(name="vote", description="Ouvrir, lister ou voter sur une décision.")
    @app_commands.describe(
        action="list (défaut), open, ou cast",
        title="Titre (pour open)",
        threshold="Seuil 0-1 (défaut 0.8)",
        vote_id="Identifiant du vote (pour cast)",
        choice="yes|no|abstain (pour cast)",
    )
    async def vote(
        interaction: discord.Interaction,
        action: str = "list",
        title: str | None = None,
        threshold: float = 0.8,
        vote_id: str | None = None,
        choice: str | None = None,
    ):
        governance = _svc("governance")
        if governance is None:
            await interaction.response.send_message("Service indisponible.", ephemeral=True)
            return
        from services.governance import VoteSpec

        if action == "open":
            if not title:
                await interaction.response.send_message(
                    "Précise un `title` pour ouvrir un vote.", ephemeral=True
                )
                return
            v = governance.create_vote(str(interaction.user.id),
                                       VoteSpec(title=title, threshold=threshold))
            await interaction.response.send_message(
                f"Vote ouvert : « {v.title} » (seuil {int(v.threshold*100)}%). "
                f"Identifiant : `{v.id[:8]}`. Votez avec `/vote action:cast vote_id:{v.id[:8]} "
                f"choice:yes`."
            )
            return
        if action == "cast":
            if not vote_id or choice not in {"yes", "no", "abstain"}:
                await interaction.response.send_message(
                    "Précise `vote_id` et `choice` (yes|no|abstain).", ephemeral=True
                )
                return
            full_id = _resolve_vote(bot, vote_id)
            if full_id is None:
                await interaction.response.send_message("Vote introuvable.", ephemeral=True)
                return
            from bot.ui import ConfirmView

            async def _confirm(inter: discord.Interaction):
                result = governance.cast_ballot(full_id, str(interaction.user.id), choice)
                audit(str(interaction.user.id), "vote_cast",
                      args={"vote": full_id, "choice": choice})
                verdict = "atteint" if result.passed else "pas encore atteint"
                await inter.followup.send(
                    f"Vote enregistré. Oui {result.yes} / Non {result.no} / "
                    f"Abst. {result.abstain} — seuil {int(result.threshold*100)}% {verdict}.",
                )

            view = ConfirmView(interaction.user.id, _confirm)
            await interaction.response.send_message(
                f"Tu votes **{choice}**. Confirmes-tu ton bulletin ?", view=view, ephemeral=True
            )
            return
        votes = governance.list_open_votes()
        if not votes:
            await interaction.response.send_message("Aucun vote ouvert.", ephemeral=True)
            return
        body = "\n".join(
            f"- « {v.title} » · seuil {int(v.threshold*100)}% · `{v.id[:8]}`" for v in votes
        )
        await interaction.response.send_message(f"**Votes ouverts :**\n{body}")


def _resolve_entity(bot, needle: str):
    """Resolve an entity by id prefix or title substring. Returns (id, title)."""
    needle = needle.strip()
    row = bot.db.query_app_one(
        "SELECT id, title FROM entities WHERE id = ? OR id LIKE ?",
        (needle, needle + "%"),
    )
    if row is None:
        row = bot.db.query_app_one(
            "SELECT id, title FROM entities WHERE title LIKE ? "
            "AND phase != 'archived' ORDER BY updated_at DESC LIMIT 1",
            (f"%{needle}%",),
        )
    return (row["id"], row["title"]) if row else None


def _resolve_vote(bot, needle: str):
    needle = needle.strip()
    row = bot.db.query_app_one(
        "SELECT id FROM votes WHERE id = ? OR id LIKE ?", (needle, needle + "%")
    )
    return row["id"] if row else None


async def _llm_summarize(bot, text: str) -> str | None:
    """Summarize channel text with the local model; None if unavailable."""
    if not await bot.ollama.ping():
        return None
    prompt = (
        "Résume en français, de façon neutre et bienveillante, les points clés et "
        "les points de vue de cette discussion de salon. Sois concise (5 puces max). "
        "N'affirme rien d'incertain.\n\n" + text[:6000]
    )
    try:
        return await bot.ollama.chat(
            [
                {"role": "system", "content": "Tu es Tramice721, une IA de médiation."},
                {"role": "user", "content": prompt},
            ]
        )
    except Exception:  # noqa: BLE001
        return None
