"""APScheduler background jobs (spec §8).

All jobs run in the bot's asyncio loop, in the configured timezone
(``America/Montreal`` by default). Each job logs start/end and row counts.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ai.rag.ingest import ingest_docs, ingest_history_rows
from bot.observability import log_job

log = logging.getLogger("tramice.scheduler")


def _wrap_job(job_id: str, fn):
    """Wrap a job coroutine with duration + status logging."""

    async def _runner() -> None:
        started = time.monotonic()
        status = "ok"
        fields: dict = {}
        try:
            await fn(fields)
        except Exception:  # noqa: BLE001
            status = "error"
            log.exception("job:%s failed", job_id)
        finally:
            log_job(
                job_id=job_id,
                duration_ms=(time.monotonic() - started) * 1000,
                status=status,
                **fields,
            )

    return _runner


def build_scheduler(bot) -> AsyncIOScheduler:
    settings = bot.settings
    services = bot.services
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    tz = settings.timezone

    async def index_new_messages(fields: dict) -> None:
        log.info("job:index_new_messages start")
        rows = bot.history.fetch_unindexed(limit=500, include_dm=False)
        if not rows:
            log.info("job:index_new_messages nothing to index")
            fields["rows"] = 0
            return
        result = ingest_history_rows(settings, rows)
        bot.history.mark_indexed([r["id"] for r in rows])
        fields["rows"] = len(rows)
        fields["chunks"] = result.chunks
        log.info("job:index_new_messages indexed %d chunks", result.chunks)

    async def refresh_knowledge_base(fields: dict) -> None:
        log.info("job:refresh_knowledge_base start")
        result = ingest_docs(settings, reset=True)
        fields["chunks"] = result.chunks
        log.info("job:refresh_knowledge_base %d chunks", result.chunks)

    async def build_daily_summary(fields: dict) -> None:
        log.info("job:build_daily_summary start")
        channel_id = settings.summary_channel_id
        guild_id = settings.guild_id
        if not channel_id or not guild_id:
            log.info("job:build_daily_summary skipped (no summary_channel_id/guild)")
            fields["skipped"] = True
            return
        now = datetime.now(timezone.utc)
        since = (now - timedelta(hours=24)).isoformat()
        rows = bot.history.fetch_guild_between(guild_id, since, now.isoformat())
        fields["messages"] = len(rows)
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

    async def game_week_open(fields: dict) -> None:
        log.info("job:game_week_open start")
        if services is None or services.game is None:
            fields["skipped"] = True
            return
        week = services.game.get_current_week()
        services.game.set_week_status(week.week_id, "investing")
        budget = services.game.compute_influence_budget(week.week_id)
        fields["week_id"] = week.week_id
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
        from bot.discord_actions import create_scheduled_event

        discord_eid = await create_scheduled_event(
            bot,
            title=f"Semaine jeu {week.week_id}",
            description=msg[:900],
            starts_at=datetime.now(timezone.utc).isoformat(),
            location="Discord — La Guilde",
            duration_min=180,
        )
        fields["discord_event_id"] = discord_eid

    async def game_week_close(fields: dict) -> None:
        log.info("job:game_week_close start")
        if services is None or services.game is None:
            fields["skipped"] = True
            return
        week = services.game.get_current_week()
        n = services.game.finalize_allocations(week.week_id)
        fields["week_id"] = week.week_id
        fields["allocations"] = n
        msg = (
            f"🌙 **Clôture de la semaine {week.week_id}**\n"
            f"Fenêtre d'investissement fermée. {n} entité·s ont reçu des allocations. "
            f"Les HOP deviennent réels après validation par les pairs."
        )
        if settings.summary_channel_id:
            await bot.post_to_channel(settings.summary_channel_id, msg)

    scheduler.add_job(
        _wrap_job("index_new_messages", index_new_messages),
        CronTrigger(hour=2, minute=0, timezone=tz),
        id="index_new_messages",
    )
    scheduler.add_job(
        _wrap_job("refresh_knowledge_base", refresh_knowledge_base),
        CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=tz),
        id="refresh_knowledge_base",
    )
    scheduler.add_job(
        _wrap_job("build_daily_summary", build_daily_summary),
        CronTrigger(hour=8, minute=0, timezone=tz),
        id="build_daily_summary",
    )
    scheduler.add_job(
        _wrap_job("game_week_open", game_week_open),
        CronTrigger(day_of_week="thu", hour=17, minute=0, timezone=tz),
        id="game_week_open",
    )
    scheduler.add_job(
        _wrap_job("game_week_close", game_week_close),
        CronTrigger(day_of_week="sun", hour=23, minute=59, timezone=tz),
        id="game_week_close",
    )

    async def capability_scan(fields: dict) -> None:
        from bot.capabilities import scan_capabilities

        snap = await scan_capabilities(bot)
        fields["guild_id"] = snap.get("guild_id")
        fields["channels"] = len(snap.get("channels") or {})

    scheduler.add_job(
        _wrap_job("capability_scan", capability_scan),
        CronTrigger(hour=4, minute=0, timezone=tz),
        id="capability_scan",
    )
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
