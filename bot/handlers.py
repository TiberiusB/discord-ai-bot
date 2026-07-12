"""Trigger detection, channel policy, and request building (spec §3.1, §7.2)."""

from __future__ import annotations

import discord

from ai.guardrails import sanitize_input
from bot.config import Settings
from bot.router import AgentRequest


def channel_allowed(settings: Settings, channel_id: str, is_dm: bool) -> bool:
    """Whether the bot may act in this channel (PLT-6 + §10.1).

    DMs are always allowed (personal-tramice surface). For salons the
    ``channels.log_mode`` policy governs allow/deny lists.
    """
    if is_dm:
        return True
    mode = settings.get("channels.log_mode", "allowlist")
    allowlist = {str(c) for c in settings.get("channels.allowlist", []) or []}
    denylist = {str(c) for c in settings.get("channels.denylist", []) or []}
    cid = str(channel_id)
    if mode == "all":
        return cid not in denylist
    if mode == "denylist":
        return cid not in denylist
    # allowlist mode: empty allowlist means "act everywhere not denied" so the
    # bot is usable before an operator curates the list.
    if not allowlist:
        return cid not in denylist
    return cid in allowlist


def should_log(settings: Settings, channel_id: str, is_dm: bool) -> bool:
    """Whether a message should be logged to community memory (MEM-1)."""
    if is_dm:
        # DMs are logged in the private tier (spec §7.4) but still recorded so
        # the personal tramice can remember; they never enter public summaries.
        return True
    return channel_allowed(settings, channel_id, is_dm)


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
