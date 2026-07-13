"""Startup validation before connecting to Discord."""

from __future__ import annotations

import logging

from bot.config import Settings

log = logging.getLogger("tramice.startup")


def validate_launch_config(settings: Settings) -> list[str]:
    """Return human-readable warnings for risky pre-launch configuration."""
    warnings: list[str] = []
    mode = settings.get("channels.log_mode", "allowlist")
    allowlist = settings.get("channels.allowlist", []) or []

    if mode == "allowlist" and not allowlist:
        warnings.append(
            "channels.allowlist is empty in allowlist mode: the bot will only "
            "respond in DMs until you add channel IDs to config.yaml."
        )

    if mode == "all":
        warnings.append(
            "channels.log_mode is 'all': every readable salon will be logged. "
            "Prefer allowlist mode for a controlled playtest."
        )

    if not settings.guild_id:
        warnings.append(
            "GUILD_ID is not set: slash commands will sync globally and may "
            "take up to an hour to appear."
        )

    if not settings.admin_role_ids:
        warnings.append(
            "ADMIN_ROLE_IDS is empty: only the guild owner can run admin commands."
        )

    return warnings


def log_launch_warnings(settings: Settings) -> None:
    for message in validate_launch_config(settings):
        log.warning("Launch config: %s", message)
