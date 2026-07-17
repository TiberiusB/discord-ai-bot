"""Trigger detection, channel policy, and request building (spec §3.1, §7.2)."""

from __future__ import annotations

import discord

from ai.guardrails import sanitize_input
from bot.channel_policy import channel_in_interact, channel_in_log
from bot.config import Settings
from bot.router import AgentRequest


def channel_allowed(settings: Settings, channel_id: str, is_dm: bool) -> bool:
    """Whether the bot may reply / accept triggers in this channel (PLT-6)."""
    return channel_in_interact(settings, channel_id, is_dm)


def should_log(settings: Settings, channel_id: str, is_dm: bool) -> bool:
    """Whether a message should be logged to community memory (MEM-1)."""
    return channel_in_log(settings, channel_id, is_dm)


def detect_trigger(
    message: discord.Message, bot_user: discord.ClientUser, prefix: str
) -> tuple[str, str] | None:
    """Return (trigger, cleaned_content) if the message addresses the bot.

    ``trigger`` is one of ``prefix`` / ``mention``. Returns ``None`` otherwise.
    DMs always count as addressing the bot.
    """
    content = message.content or ""
    is_dm = message.guild is None

    if content.startswith(prefix):
        return "prefix", content[len(prefix):].strip()

    if bot_user in message.mentions:
        cleaned = content.replace(f"<@{bot_user.id}>", "").replace(
            f"<@!{bot_user.id}>", ""
        ).strip()
        return "mention", cleaned

    if is_dm:
        return "mention", content.strip()

    return None


def make_request(
    *,
    guild_id: str | None,
    channel_id: str,
    user_id: str,
    user_name: str | None,
    is_dm: bool,
    content: str,
    trigger: str,
    command: str | None = None,
) -> AgentRequest:
    return AgentRequest(
        guild_id=guild_id,
        channel_id=channel_id,
        user_id=user_id,
        surface="dm" if is_dm else "salon",
        thread_id=f"{user_id}-{channel_id}",
        content=sanitize_input(content),
        trigger=trigger,  # type: ignore[arg-type]
        command=command,
        user_name=user_name,
    )
