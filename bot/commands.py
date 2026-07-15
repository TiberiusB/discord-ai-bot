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
from bot.router import SubmitStatus
from bot.ui import MODEL_RESET_VALUE, ModelSelectView

log = logging.getLogger("tramice.commands")

PERM_DENIED = "Je n'ai pas la permission pour cette action."

_MODEL_ADMIN_INFO = (
    "ℹ️ `/model` change le modèle par défaut pour **toute la communauté** "
    "(sauf les tramarades ayant choisi le leur avec `/modele`). Le choix "
    "n'est pas persisté : il revient à `config.yaml` au redémarrage."
)

_MODEL_CAUTION = (
    "ℹ️ **À savoir :** chaque modèle a son caractère. La qualité des réponses, "
    "la vitesse et l'aptitude à utiliser mes outils varient d'un modèle à "
    "l'autre — sur CPU, un modèle plus grand (ex. `gemma2:9b`) répond plus "
    "lentement, et certains modèles suivent moins bien les commandes d'outils. "
    "Ton choix **ne concerne que tes échanges**, reste en mémoire et s'applique "
    "dès ton prochain message ; notre fil de conversation est conservé. Reviens "
    "au modèle par défaut à tout moment avec `/modele nom:defaut`."
)

_RESET_ALIASES = {"defaut", "défaut", "default", "auto", "reset", "0"}

REINDEX_SCOPE_CHOICES = [
    app_commands.Choice(name="Documents locaux (docs/)", value="docs"),
    app_commands.Choice(name="Sources web curatées", value="web"),
    app_commands.Choice(name="Documents + web", value="all"),
]


def _format_reindex_result(result: dict) -> str:
    scope = result.get("scope", "docs")
    lines = [f"Index reconstruit (scope : **{scope}**). 📚"]
    if "docs" in result:
        docs = result["docs"]
        lines.append(
            f"- **docs** : {docs['documents']} documents, {docs['chunks']} fragments"
        )
    if "web" in result:
        web = result["web"]
        lines.append(
            f"- **web** : {web['sources']} source(s), {web['total_pages']} page(s), "
            f"{web['total_chunks']} fragment(s)"
        )
        if web.get("errors"):
            lines.append("- **erreurs** :")
            for err in web["errors"][:5]:
                lines.append(f"  - {err[:200]}")
    return "\n".join(lines)


def _format_web_sources_list(sources) -> str:
    if not sources:
        return "Aucune source web curatée pour l'instant."
    lines = ["**Sources web indexées** :\n"]
    for src in sources:
        label = src.label or src.seed_url
        status = (
            f"{src.last_page_count} page(s), {src.last_chunk_count} fragment(s)"
            if src.last_indexed_at
            else "pas encore indexée"
        )
        indexed = src.last_indexed_at or "—"
        err = f"\n  ⚠️ {src.last_error[:150]}" if src.last_error else ""
        lines.append(
            f"**#{src.id}** — {label}\n"
            f"  URL : {src.seed_url}\n"
            f"  Domaine : {src.domain} | profondeur {src.max_depth} | max {src.max_pages} pages\n"
            f"  Indexé : {indexed} | {status}{err}"
        )
    return "\n".join(lines)


def _is_embed_model(name: str, embed_model: str) -> bool:
    base = name.split(":", 1)[0]
    embed_base = embed_model.split(":", 1)[0]
    return base == embed_base


def _filter_chat_models(models: list[str], embed_model: str) -> list[str]:
    return [m for m in models if not _is_embed_model(m, embed_model)]


async def _tools_warning(ollama, choice: str) -> str:
    if await ollama.supports_tools(choice):
        return ""
    return (
        f"\n\n⚠️ **{choice}** ne gère pas l'appel d'outils : je répondrai "
        "avec ma personnalité et ma mémoire, mais sans mes outils (recherche "
        "dans les connaissances, volios, événements…). Pour ces fonctions, "
        "choisis un modèle compatible (ex. `qwen2.5:7b-instruct`) ou reviens "
        "au défaut avec `/modele nom:defaut`."
    )


async def _apply_admin_model(
    bot, interaction: discord.Interaction, name: str, available: list[str]
) -> None:
    if available and name not in available:
        listing = "\n".join(f"- {m}" for m in available) or "(aucun modèle trouvé)"
        await interaction.followup.send(
            f"Le modèle `{name}` n'est pas installé. Fais `ollama pull {name}` "
            f"d'abord.\nModèles disponibles :\n{listing}",
            ephemeral=True,
        )
        return
    bot.ollama.set_model(name)
    audit(str(interaction.user.id), "model_swap", args={"model": name})
    if getattr(bot, "on_model_changed", None):
        bot.on_model_changed(name)
    await interaction.followup.send(
        f"Nouvelle âme par défaut chargée : **{name}**. 🌱\n"
        "S'applique à tous, sauf aux tramarades ayant un modèle personnel "
        "(`/modele`). Non persisté : retour à `config.yaml` au redémarrage.",
        ephemeral=True,
    )


async def _apply_user_model(
    bot,
    interaction: discord.Interaction,
    user_id: str,
    choice: str,
    available: list[str],
    *,
    default_model: str,
) -> None:
    if choice.lower() in _RESET_ALIASES:
        bot.db.clear_user_model(user_id)
        audit(user_id, "user_model_reset")
        await interaction.followup.send(
            f"C'est noté — tu utilises de nouveau le modèle par défaut : "
            f"**{default_model}**. 🌱\nEffet dès ton prochain message ; notre fil "
            "de conversation reste intact.",
            ephemeral=True,
        )
        return
    if available and choice not in available:
        listing = "\n".join(f"- {m}" for m in available) or "(aucun modèle trouvé)"
        await interaction.followup.send(
            f"Le modèle `{choice}` n'est pas installé, je ne peux pas l'utiliser.\n"
            f"Modèles disponibles :\n{listing}\n\n"
            "Un admin peut en installer d'autres avec `ollama pull <modèle>`.",
            ephemeral=True,
        )
        return
    bot.db.set_user_model(user_id, choice)
    audit(user_id, "user_model_set", args={"model": choice})
    tools_note = await _tools_warning(bot.ollama, choice)
    await interaction.followup.send(
        f"C'est fait — tes échanges utiliseront désormais **{choice}**. 🌱"
        f"{tools_note}\n\n{_MODEL_CAUTION}",
        ephemeral=True,
    )


async def _run_agent_interaction(
    bot, interaction: discord.Interaction, content: str, command: str
) -> None:
    """Defer an interaction, route it through the queue, reply via followup."""
    from bot.discord_errors import log_discord_error

    try:
        await interaction.response.defer(thinking=True)
    except discord.DiscordException as exc:
        log_discord_error(
            log,
            "Failed to defer slash interaction",
            exc,
            event=f"slash:{command}.defer",
            user_id=interaction.user.id,
        )
        return
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
    result = await bot.router.submit(req)
    if result.status is not SubmitStatus.ACCEPTED and result.message:
        try:
            await interaction.followup.send(result.message)
        except discord.DiscordException as exc:
            log_discord_error(
                log,
                "Failed to send router rejection",
                exc,
                event=f"slash:{command}.reject",
                user_id=interaction.user.id,
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
            f"- fils de conversation supprimés : {result.checkpoints_deleted}\n"
            f"- fragments RAG supprimés : {result.history_embeddings_deleted}\n"
            f"- profil supprimé : {'oui' if result.profile_deleted else 'non'}\n"
            f"- trace d'activité conservée : {'oui' if result.trace_recorded else 'non'}"
        )

    @tree.command(
        name="say",
        description="[Admin] Publier un message en synthèse vocale (TTS).",
    )
    @app_commands.describe(text="Texte à lire (max 500 caractères)")
    async def say(interaction: discord.Interaction, text: str):
        if not bot.is_admin(interaction):
            await interaction.response.send_message(PERM_DENIED, ephemeral=True)
            return
        if not bot.settings.get("features.tts", False):
            await interaction.response.send_message(
                "La synthèse vocale est désactivée (`features.tts`).", ephemeral=True
            )
            return
        if interaction.guild is None:
            await interaction.response.send_message(
                "Le TTS fonctionne dans un salon du serveur.", ephemeral=True
            )
            return
        from ai.guardrails import sanitize_input
        from bot.capabilities import can, load_capabilities_snapshot
        from bot.handlers import channel_allowed

        channel_id = str(interaction.channel_id)
        if not channel_allowed(bot.settings, channel_id, is_dm=False):
            await interaction.response.send_message(
                "Ce salon n'est pas autorisé.", ephemeral=True
            )
            return
        snap = load_capabilities_snapshot(bot.settings)
        if not can(snap, "send_tts_messages", channel_id):
            await interaction.response.send_message(
                "Je n'ai pas la permission SEND_TTS_MESSAGES ici.", ephemeral=True
            )
            return
        cleaned = sanitize_input(text)[:500].strip()
        if not cleaned:
            await interaction.response.send_message("Texte vide.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.channel.send(cleaned, tts=True)  # type: ignore[union-attr]
            audit(str(interaction.user.id), "say_tts", result="ok")
            await interaction.followup.send("Message TTS envoyé. 🔊", ephemeral=True)
        except discord.DiscordException as exc:
            await interaction.followup.send(f"Échec TTS : {exc}", ephemeral=True)

    @tree.command(
        name="reindex",
        description="[Admin] Reconstruire l'index RAG (documents locaux et/ou web).",
    )
    @app_commands.describe(
        scope="Quoi réindexer : docs locaux, sources web, ou les deux"
    )
    @app_commands.choices(scope=REINDEX_SCOPE_CHOICES)
    async def reindex(
        interaction: discord.Interaction,
        scope: app_commands.Choice[str] | None = None,
    ):
        if not bot.is_admin(interaction):
            await interaction.response.send_message(PERM_DENIED, ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        services = bot.services
        if services is None or services.knowledge is None:
            await interaction.followup.send("Le service de connaissances n'est pas prêt.")
            return
        selected = scope.value if scope else "docs"
        try:
            result = await bot.loop.run_in_executor(
                None, lambda: services.knowledge.reindex(selected)
            )
        except Exception as exc:  # noqa: BLE001
            await interaction.followup.send(
                "L'indexation a échoué. Vérifie qu'Ollama tourne et que le modèle "
                f"d'embedding est installé (`ollama pull {bot.settings.embed_model}`).\n"
                f"Détail : {exc}"
            )
            return
        audit(
            str(interaction.user.id),
            "reindex",
            args={"scope": selected},
            result="ok",
        )
        await interaction.followup.send(_format_reindex_result(result))

    web_source = app_commands.Group(
        name="web-source",
        description="[Admin] Gérer les sources web curatées pour la mémoire RAG.",
    )

    @web_source.command(
        name="add",
        description="[Admin] Ajouter et indexer une source web (crawl même domaine).",
    )
    @app_commands.describe(
        url="URL de départ (page d'accueil ou page cible)",
        label="Nom lisible pour les curateurs (facultatif)",
        max_depth="Profondeur de crawl (défaut : config rag.web.max_depth)",
        max_pages="Nombre max de pages (défaut : config rag.web.max_pages)",
    )
    async def web_source_add(
        interaction: discord.Interaction,
        url: str,
        label: str | None = None,
        max_depth: app_commands.Range[int, 0, 5] | None = None,
        max_pages: app_commands.Range[int, 1, 100] | None = None,
    ):
        if not bot.is_admin(interaction):
            await interaction.response.send_message(PERM_DENIED, ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        services = bot.services
        if services is None or services.knowledge is None:
            await interaction.followup.send("Le service de connaissances n'est pas prêt.")
            return
        from ai.rag.web_ingest import WebIngestError

        try:
            result = await bot.loop.run_in_executor(
                None,
                lambda: services.knowledge.add_web_source(
                    url,
                    str(interaction.user.id),
                    label=label,
                    max_depth=max_depth,
                    max_pages=max_pages,
                ),
            )
        except WebIngestError as exc:
            await interaction.followup.send(f"Source web refusée : {exc}")
            return
        except Exception as exc:  # noqa: BLE001
            await interaction.followup.send(
                "L'indexation web a échoué. Vérifie qu'Ollama tourne.\n"
                f"Détail : {exc}"
            )
            return
        audit(
            str(interaction.user.id),
            "web_source_add",
            args={"url": result["seed_url"], "label": label},
            result="ok",
        )
        display = label or result["seed_url"]
        await interaction.followup.send(
            f"Source web **{display}** indexée. 🌐\n"
            f"- URL : {result['seed_url']}\n"
            f"- Domaine : {result['domain']}\n"
            f"- {result['pages']} page(s), {result['chunks']} fragment(s) dans la collection « web »."
        )

    @web_source.command(
        name="list",
        description="[Admin] Lister les sources web curatées et leur statut d'indexation.",
    )
    async def web_source_list(interaction: discord.Interaction):
        if not bot.is_admin(interaction):
            await interaction.response.send_message(PERM_DENIED, ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        services = bot.services
        if services is None or services.knowledge is None:
            await interaction.followup.send("Le service de connaissances n'est pas prêt.")
            return
        sources = services.knowledge.list_web_sources()
        text = _format_web_sources_list(sources)
        if len(text) > 1900:
            text = text[:1900] + "\n… (liste tronquée)"
        await interaction.followup.send(text)

    @web_source.command(
        name="remove",
        description="[Admin] Retirer une source web et supprimer ses fragments RAG.",
    )
    @app_commands.describe(
        url_or_id="URL seed enregistrée ou identifiant (#id de /web-source list)"
    )
    async def web_source_remove(interaction: discord.Interaction, url_or_id: str):
        if not bot.is_admin(interaction):
            await interaction.response.send_message(PERM_DENIED, ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        services = bot.services
        if services is None or services.knowledge is None:
            await interaction.followup.send("Le service de connaissances n'est pas prêt.")
            return
        from ai.rag.web_ingest import WebIngestError

        try:
            result = await bot.loop.run_in_executor(
                None,
                lambda: services.knowledge.remove_web_source(url_or_id.strip()),
            )
        except WebIngestError as exc:
            await interaction.followup.send(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            await interaction.followup.send(f"Échec de suppression : {exc}")
            return
        audit(
            str(interaction.user.id),
            "web_source_remove",
            args={"seed_url": result["seed_url"]},
            result="ok",
        )
        await interaction.followup.send(
            f"Source **#{result['id']}** retirée ({result['seed_url']}). "
            f"{result['chunks_deleted']} fragment(s) supprimé(s) de Chroma."
        )

    tree.add_command(web_source)

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
            "",
            "**Discord / runtime :**",
            *bot.health_snapshot_lines(),
        ]
        await interaction.followup.send("\n".join(lines))

    @tree.command(
        name="model",
        description="[Admin] Changer le modèle Ollama par défaut (toute la communauté).",
    )
    @app_commands.describe(name="Nom du modèle Ollama (laisser vide pour le menu)")
    async def model(interaction: discord.Interaction, name: str | None = None):
        if not bot.is_admin(interaction):
            await interaction.response.send_message(PERM_DENIED, ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        embed_model = bot.settings.embed_model
        available = _filter_chat_models(await bot.ollama.list_models(), embed_model)
        if not name:
            current = bot.ollama.model
            listing = "\n".join(f"- {m}" for m in available) or "(aucun modèle trouvé)"
            body = (
                f"Modèle par défaut actuel : **{current}**\n\n"
                f"Modèles disponibles :\n{listing}\n\n"
                f"{_MODEL_ADMIN_INFO}\n\n"
                "**Choisis un modèle dans le menu ci-dessous :**"
            )

            async def _on_admin_pick(
                inter: discord.Interaction, choice: str
            ) -> None:
                await _apply_admin_model(bot, inter, choice, available)

            view = ModelSelectView(
                author_id=interaction.user.id,
                models=available,
                body=body,
                current=current,
                on_pick=_on_admin_pick,
                placeholder="Modèle par défaut pour la communauté…",
            )
            await interaction.followup.send(body, view=view, ephemeral=True)
            return
        await _apply_admin_model(bot, interaction, name.strip(), available)

    @tree.command(
        name="modele",
        description="Choisir ton modèle d'IA personnel (n'affecte que tes échanges).",
    )
    @app_commands.describe(
        nom="Nom du modèle (vide pour le menu ; « defaut » pour réinitialiser)"
    )
    async def modele(interaction: discord.Interaction, nom: str | None = None):
        await interaction.response.defer(thinking=True, ephemeral=True)
        user_id = str(interaction.user.id)
        embed_model = bot.settings.embed_model
        available = _filter_chat_models(await bot.ollama.list_models(), embed_model)
        default_model = bot.ollama.model
        current_pref = bot.db.get_user_model(user_id)

        if not nom:
            listing = "\n".join(f"- {m}" for m in available) or "(aucun modèle trouvé)"
            if current_pref:
                head = (
                    f"Ton modèle personnel : **{current_pref}**\n"
                    f"(Modèle par défaut de la communauté : `{default_model}`.)"
                )
            else:
                head = f"Tu utilises le modèle par défaut : **{default_model}**"
            body = (
                f"{head}\n\nModèles disponibles :\n{listing}\n\n"
                "**Choisis un modèle dans le menu ci-dessous** "
                "(ou tape `/modele nom:<modèle>` / `/modele nom:defaut`).\n\n"
                f"{_MODEL_CAUTION}"
            )
            current = current_pref or default_model

            async def _on_user_pick(
                inter: discord.Interaction, choice: str
            ) -> None:
                if choice == MODEL_RESET_VALUE:
                    choice = "defaut"
                await _apply_user_model(
                    bot,
                    inter,
                    user_id,
                    choice,
                    available,
                    default_model=default_model,
                )

            view = ModelSelectView(
                author_id=interaction.user.id,
                models=available,
                body=body,
                current=current,
                include_reset=True,
                default_label=default_model,
                on_pick=_on_user_pick,
                placeholder="Ton modèle personnel…",
            )
            await interaction.followup.send(body, view=view, ephemeral=True)
            return

        await _apply_user_model(
            bot,
            interaction,
            user_id,
            nom.strip(),
            available,
            default_model=default_model,
        )

    @modele.autocomplete("nom")
    async def modele_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        try:
            embed_model = bot.settings.embed_model
            available = _filter_chat_models(
                await bot.ollama.list_models(), embed_model
            )
        except Exception:  # noqa: BLE001 - autocomplete must never raise
            available = []
        needle = (current or "").lower()
        choices: list[app_commands.Choice[str]] = []
        if not needle or needle in "defaut":
            choices.append(
                app_commands.Choice(name="defaut (modèle par défaut)", value="defaut")
            )
        for name in available:
            if needle in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
        return choices[:25]

    register_m4_commands(bot)
    register_post_mvp_commands(bot)
    if bot.settings.get("features.game_simulation", True):
        register_m5_commands(bot)
    log.info(
        "Registered slash commands: /ask, /forgetme, /reindex, /web-source, /model, /modele, "
        "/health, /say, /volio, /mondo, /echoes, /event, /summarize, /normes, "
        "/norm-set, /signalement, /identite, /thread, /sondage, /son, "
        "/mission, /place, /vote"
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
                from bot.discord_actions import create_scheduled_event

                discord_eid = await create_scheduled_event(
                    bot,
                    title=created.title,
                    starts_at=when,
                    location=location,
                    description=created.title,
                )
                if discord_eid:
                    coordination.attach_discord_event_id(created.id, discord_eid)
                audit(str(interaction.user.id), "event_confirm", args={"event": created.id})
                extra = " (événement Discord créé)" if discord_eid else ""
                await inter.followup.send(
                    f"Événement confirmé : **{created.title}**.{extra} 🎉",
                    ephemeral=False,
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
        suggestion = governance.evaluate_moderation(str(target.id) if target else None)
        if suggestion and interaction.guild_id:
            sent = await bot.dm_admins(str(interaction.guild_id), suggestion.message)
            audit(
                str(interaction.user.id),
                "moderation_suggestion",
                args={"target": suggestion.target_id, "dms_sent": sent},
            )
        await interaction.response.send_message(
            f"Signalement enregistré (n°{sig_id}, niveau {max(1, min(3, level))}). "
            "Je privilégie d'abord la médiation. 🕊️",
            ephemeral=True,
        )


def register_post_mvp_commands(bot) -> None:
    """Post-MVP: identity, threads, polls, soundboard."""
    tree = bot.tree
    services = bot.services

    def _svc(name):
        return getattr(services, name, None) if services else None

    @tree.command(
        name="identite",
        description="Gérer les noms connus d'un membre ou lier des identités.",
    )
    @app_commands.describe(
        action="noms (lister) ou lier (associer deux comptes)",
        membre="Membre concerné (défaut : toi)",
        autre="Second membre (pour lier)",
    )
    async def identite(
        interaction: discord.Interaction,
        action: str = "noms",
        membre: discord.Member | None = None,
        autre: discord.Member | None = None,
    ):
        identity = _svc("identity")
        if identity is None:
            await interaction.response.send_message("Service indisponible.", ephemeral=True)
            return
        subject = membre or interaction.user
        uid = str(subject.id)
        if action == "lier":
            if autre is None:
                await interaction.response.send_message(
                    "Précise `autre` pour lier deux identités.", ephemeral=True
                )
                return
            if uid == str(autre.id) and not bot.is_admin(interaction):
                await interaction.response.send_message(
                    "Tu ne peux pas lier ton compte à lui-même.", ephemeral=True
                )
                return
            if not bot.is_admin(interaction) and (
                str(interaction.user.id) not in {uid, str(autre.id)}
            ):
                await interaction.response.send_message(PERM_DENIED, ephemeral=True)
                return
            try:
                identity.link_identities(uid, str(autre.id), str(interaction.user.id))
            except ValueError as exc:
                await interaction.response.send_message(str(exc), ephemeral=True)
                return
            audit(
                str(interaction.user.id),
                "identity_link",
                args={"a": uid, "b": str(autre.id)},
            )
            await interaction.response.send_message(
                f"Identités liées : {subject.display_name} ↔ {autre.display_name}.",
                ephemeral=True,
            )
            return
        names = identity.list_aliases(uid)
        if not names:
            identity.record_alias(uid, subject.display_name)
            names = identity.list_aliases(uid)
        body = "\n".join(f"- {n}" for n in names) or "(aucun nom enregistré)"
        await interaction.response.send_message(
            f"**Noms connus pour {subject.display_name} :**\n{body}",
            ephemeral=True,
        )

    @tree.command(name="thread", description="Créer un fil de discussion dans ce salon.")
    @app_commands.describe(nom="Nom du fil", message="Premier message (facultatif)")
    async def thread_cmd(
        interaction: discord.Interaction,
        nom: str,
        message: str | None = None,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "Les fils se créent dans un salon du serveur.", ephemeral=True
            )
            return
        from bot.discord_actions import create_channel_thread
        from bot.handlers import channel_allowed

        channel_id = str(interaction.channel_id)
        if not channel_allowed(bot.settings, channel_id, is_dm=False):
            await interaction.response.send_message(
                "Ce salon n'est pas autorisé.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        thread = await create_channel_thread(bot, channel_id, nom, message)
        if thread is None:
            await interaction.followup.send(
                "Impossible de créer le fil (permission ou type de salon).",
                ephemeral=True,
            )
            return
        audit(str(interaction.user.id), "create_thread", args={"name": nom})
        await interaction.followup.send(
            f"Fil créé : {thread.mention}", ephemeral=True
        )

    @tree.command(name="sondage", description="Créer un sondage dans ce salon.")
    @app_commands.describe(
        question="Question du sondage",
        option1="Option 1",
        option2="Option 2",
        option3="Option 3 (facultatif)",
        option4="Option 4 (facultatif)",
    )
    async def sondage(
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str | None = None,
        option4: str | None = None,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "Les sondages se créent dans un salon.", ephemeral=True
            )
            return
        from bot.handlers import channel_allowed

        if not channel_allowed(bot.settings, str(interaction.channel_id), is_dm=False):
            await interaction.response.send_message(
                "Ce salon n'est pas autorisé.", ephemeral=True
            )
            return
        options = [o for o in (option1, option2, option3, option4) if o and o.strip()]
        if len(options) < 2:
            await interaction.response.send_message(
                "Au moins deux options sont requises.", ephemeral=True
            )
            return
        poll = discord.Poll(
            question=question[:300],
            answers=[discord.PollAnswer(text=o[:55]) for o in options[:10]],
            duration=24,
        )
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.channel.send(poll=poll)  # type: ignore[union-attr]
            audit(str(interaction.user.id), "create_poll", result="ok")
            await interaction.followup.send("Sondage publié.", ephemeral=True)
        except discord.DiscordException as exc:
            await interaction.followup.send(f"Échec du sondage : {exc}", ephemeral=True)

    @tree.command(
        name="son",
        description="Lister les sons du soundboard du serveur (lecture vocale limitée).",
    )
    async def son(interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "Le soundboard est propre au serveur.", ephemeral=True
            )
            return
        from bot.discord_actions import list_soundboard_sounds

        await interaction.response.defer(ephemeral=True)
        names = await list_soundboard_sounds(bot)
        if not names:
            await interaction.followup.send(
                "Aucun son accessible (permission USE_SOUNDBOARD ou soundboard vide). "
                "La lecture automatique en salon vocal n'est pas encore supportée.",
                ephemeral=True,
            )
            return
        body = "\n".join(f"- {n}" for n in names[:25])
        await interaction.followup.send(
            f"**Sons du soundboard :**\n{body}\n\n"
            "(La lecture automatique en vocal nécessite une connexion vocale — "
            "à venir.)",
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
                f"demandés). Les tramarades peuvent investir avec `/place`. 🚀"
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
