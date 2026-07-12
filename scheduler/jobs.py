"""APScheduler background jobs (spec §8).

All jobs run in the bot's asyncio loop, in the configured timezone
(``America/Montreal`` by default). Each job logs start/end and row counts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ai.rag.ingest import ingest_docs, ingest_history_rows

log = logging.getLogger("tramice.scheduler")


def build_scheduler(bot) -> AsyncIOScheduler:
    settings = bot.settings
    services = bot.services
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    tz = settings.timezone

    async def index_new_messages() -> None:
        log.info("job:index_new_messages start")
        rows = bot.history.fetch_unindexed(limit=500, include_dm=False)
        if not rows:
            log.info("job:index_new_messages nothing to index")
            return
        try:
            result = ingest_history_rows(settings, rows)
            bot.history.mark_indexed([r["id"] for r in rows])
            log.info("job:index_new_messages indexed %d chunks", result.chunks)
        except Exception:  # noqa: BLE001
            log.exception("job:index_new_messages failed (Ollama down?)")

    async def refresh_knowledge_base() -> None:
        log.info("job:refresh_knowledge_base start")
        try:
            result = ingest_docs(settings, reset=True)
            log.info("job:refresh_knowledge_base %d chunks", result.chunks)
        except Exception:  # noqa: BLE001
            log.exception("job:refresh_knowledge_base failed")

    async def build_daily_summary() -> None:
        log.info("job:build_daily_summary start")
        channel_id = settings.summary_channel_id
        guild_id = settings.guild_id
        if not channel_id or not guild_id:
            log.info("job:build_daily_summary skipped (no summary_channel_id/guild)")
            return
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=24)).isoformat()
        rows = bot.history.fetch_guild_between(guild_id, since, now.isoformat())
        if not rows:
            await bot.post_to_channel(
                channel_id, "Bonjour ! Rien de neuf dans les salons ces 24 heures. 🌿"
            )
            return
        text = "\n".join(f"{r['user_name'] or r['user_id']}: {r['content']}" for r in rows)
        summary = await _summarize(bot, text)
        await bot.post_to_channel(
            channel_id,
            f"**Résumé du jour ({len(rows)} messages) :**\n{summary}",
        )
        log.info("job:build_daily_summary posted (%d messages)", len(rows))

    async def game_week_open() -> None:
        log.info("job:game_week_open start")
        if services is None or services.game is None:
            return
        week = services.game.get_current_week()
        services.game.set_week_status(week.week_id, "investing")
        budget = services.game.compute_influence_budget(week.week_id)
        msg = (
            f"🌅 **Ouverture de la semaine {week.week_id}**\n"
            f"La fenêtre d'investissement est ouverte jusqu'à dimanche minuit.\n"
            f"Budget d'influence indicatif : ~{budget:.2f} HOP par trammer "
            f"(min {week.influence_min:.0f}, max {week.influence_max:.0f}).\n"
            f"Les entreprises peuvent publier leurs Missions (`/mission`), "
            f"et chacun·e peut placer son influence (`/place`)."
        )
        if settings.summary_channel_id:
            await bot.post_to_channel(settings.summary_channel_id, msg)

    async def game_week_close() -> None:
        log.info("job:game_week_close start")
        if services is None or services.game is None:
            return
        week = services.game.get_current_week()
        n = services.game.finalize_allocations(week.week_id)
        msg = (
            f"🌙 **Clôture de la semaine {week.week_id}**\n"
            f"Fenêtre d'investissement fermée. {n} entité·s ont reçu des allocations. "
            f"Les HOP deviennent réels après validation par les pairs."
        )
        if settings.summary_channel_id:
            await bot.post_to_channel(settings.summary_channel_id, msg)

    scheduler.add_job(index_new_messages, CronTrigger(hour=2, minute=0, timezone=tz),
                      id="index_new_messages")
    scheduler.add_job(refresh_knowledge_base, CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=tz),
                      id="refresh_knowledge_base")
    scheduler.add_job(build_daily_summary, CronTrigger(hour=8, minute=0, timezone=tz),
                      id="build_daily_summary")
    scheduler.add_job(game_week_open, CronTrigger(day_of_week="thu", hour=17, minute=0, timezone=tz),
                      id="game_week_open")
    scheduler.add_job(game_week_close, CronTrigger(day_of_week="sun", hour=23, minute=59, timezone=tz),
                      id="game_week_close")
    return scheduler


async def _summarize(bot, text: str) -> str:
    if not await bot.ollama.ping():
        return "(Résumé indisponible : Ollama hors ligne.)"
    prompt = (
        "Résume en français, de façon neutre et bienveillante, l'activité de la "
        "communauté ci-dessous. 5 puces maximum, ton chaleureux, n'affirme rien "
        "d'incertain.\n\n" + text[:6000]
    )
    try:
        return await bot.ollama.chat(
            [
                {"role": "system", "content": "Tu es Tramice721."},
                {"role": "user", "content": prompt},
            ]
        )
    except Exception:  # noqa: BLE001
        return "(Résumé indisponible pour le moment.)"
