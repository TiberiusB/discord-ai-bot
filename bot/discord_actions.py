"""Discord API affordances: scheduled events, threads, soundboard (post-MVP)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord

from bot.capabilities import can, load_capabilities_snapshot
from bot.discord_errors import log_discord_error

if TYPE_CHECKING:
    from bot.discord_client import TramiceBot

log = logging.getLogger("tramice.discord_actions")


def _parse_starts_at(text: str | None) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text.replace("Z", "+00:00"), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


async def create_scheduled_event(
    bot: "TramiceBot",
    *,
    title: str,
    description: str | None = None,
    starts_at: str | None = None,
    location: str | None = None,
    duration_min: int | None = 60,
) -> str | None:
    """Create a native Discord scheduled event; return its snowflake id or None."""
    settings = bot.settings
    if not settings.guild_id:
        return None
    snap = load_capabilities_snapshot(settings)
    if not can(snap, "manage_events"):
        log.info("Skipping Discord event: no MANAGE_EVENTS permission")
        return None

    guild = bot.get_guild(int(settings.guild_id))
    if guild is None:
        try:
            guild = await bot.fetch_guild(int(settings.guild_id))
        except discord.DiscordException as exc:
            log_discord_error(
                log,
                "create_scheduled_event: guild fetch failed",
                exc,
                guild_id=settings.guild_id,
            )
            return None

    start = _parse_starts_at(starts_at) or (
        datetime.now(timezone.utc) + timedelta(days=7)
    )
    end = start + timedelta(minutes=duration_min or 60)
    loc = location or "En ligne / À confirmer"
    desc = (description or title)[:1000]

    try:
        event = await guild.create_scheduled_event(
            name=title[:100],
            description=desc,
            start_time=start,
            end_time=end,
            location=loc,
            entity_type=discord.EntityType.external,
        )
        return str(event.id)
    except discord.DiscordException as exc:
        log_discord_error(log, "create_scheduled_event failed", exc, guild_id=settings.guild_id)
        return None


async def create_channel_thread(
    bot: "TramiceBot",
    channel_id: str,
    name: str,
    message: str | None = None,
) -> discord.Thread | None:
    """Create a thread in an allowlisted channel if permitted."""
    snap = load_capabilities_snapshot(bot.settings)
    if not (
        can(snap, "create_public_threads", channel_id)
        or can(snap, "create_private_threads", channel_id)
    ):
        log.info("Skipping thread: no CREATE_*_THREADS in channel %s", channel_id)
        return None

    try:
        channel = bot.get_channel(int(channel_id)) or await bot.fetch_channel(int(channel_id))
    except (discord.DiscordException, ValueError) as exc:
        log_discord_error(
            log, "create_channel_thread: channel fetch failed", exc, channel_id=channel_id
        )
        return None

    if not isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
        return None

    try:
        if isinstance(channel, discord.ForumChannel):
            thread = await channel.create_thread(name=name[:100], content=message or name)
        else:
            thread = await channel.create_thread(name=name[:100], auto_archive_duration=1440)
            if message:
                await thread.send(message[:2000])
        return thread
    except discord.DiscordException as exc:
        log_discord_error(
            log, "create_channel_thread failed", exc, channel_id=channel_id
        )
        return None


async def list_soundboard_sounds(bot: "TramiceBot") -> list[str]:
    """Return soundboard sound names if the bot can access them."""
    snap = load_capabilities_snapshot(bot.settings)
    if not can(snap, "use_soundboard") or not bot.settings.guild_id:
        return []
    guild = bot.get_guild(int(bot.settings.guild_id))
    if guild is None:
        return []
    try:
        sounds = await guild.fetch_soundboard_sounds()
        return [s.name for s in sounds]
    except discord.DiscordException as exc:
        log_discord_error(log, "fetch_soundboard_sounds failed", exc)
        return []
