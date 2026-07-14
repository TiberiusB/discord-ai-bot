"""Discord API error classification and safe send helpers."""

from __future__ import annotations

import logging
from typing import Any

import discord

from bot.observability import record_event_error

# Discord error code hints (common API failures).
_CODE_HINTS: dict[int, str] = {
    10003: "Unknown channel — vérifier channels.allowlist / summary_channel_id.",
    10004: "Unknown guild — vérifier GUILD_ID et l'invitation du bot.",
    10007: "Unknown user — l'utilisateur n'existe plus ou DM impossible.",
    10013: "Unknown user — utilisateur introuvable.",
    50001: "Missing access — le bot n'a pas accès à ce salon ou DM bloqué.",
    50007: "Cannot send messages to this user — DMs fermés.",
    50013: "Missing permissions — accorder les permissions au rôle du bot.",
    50035: "Invalid form body — contenu ou payload invalide.",
    50101: "Server needs more boosts — fonctionnalité serveur indisponible.",
}

_STATUS_HINTS: dict[int, str] = {
    401: "Non autorisé — token invalide ou révoqué.",
    403: "Interdit — permission ou accès manquant.",
    404: "Introuvable — ressource Discord absente.",
    429: "Rate limit — réessayer après le délai indiqué.",
    503: "Discord indisponible — réessayer plus tard.",
}


def describe_discord_error(exc: BaseException) -> str:
    """Return a one-line operator-friendly summary of a Discord-related error."""
    if isinstance(exc, discord.LoginFailure):
        return "Échec de connexion : DISCORD_TOKEN invalide ou révoqué."
    if isinstance(exc, discord.PrivilegedIntentsRequired):
        return (
            "Intents privilégiés manquants — activer Message Content et "
            "Server Members dans le Developer Portal."
        )
    if isinstance(exc, discord.HTTPException):
        code = getattr(exc, "code", None)
        hint = _CODE_HINTS.get(code) if code is not None else None
        if hint is None and exc.status in _STATUS_HINTS:
            hint = _STATUS_HINTS[exc.status]
        parts = [f"HTTP {exc.status}"]
        if code is not None:
            parts.append(f"code={code}")
        if exc.text:
            parts.append(str(exc.text)[:200])
        if hint:
            parts.append(f"— {hint}")
        return " ".join(parts)
    if isinstance(exc, discord.Forbidden):
        return "Interdit — permission ou accès manquant (403)."
    if isinstance(exc, discord.NotFound):
        return "Introuvable — salon, message ou ressource absent (404)."
    return f"{type(exc).__name__}: {exc}"


def log_discord_error(
    logger: logging.Logger,
    message: str,
    exc: BaseException,
    *,
    event: str | None = None,
    level: int = logging.ERROR,
    exc_info: bool | BaseException = True,
    **context: Any,
) -> str:
    """Log a classified Discord error; optionally record for /health."""
    summary = describe_discord_error(exc)
    extra = " ".join(f"{k}={v}" for k, v in context.items() if v is not None)
    log_msg = f"{message} — {summary}"
    if extra:
        log_msg = f"{log_msg} ({extra})"
    if event:
        record_event_error(event, summary)
    # Expected permission/access failures: warning without full traceback noise.
    if isinstance(exc, discord.HTTPException) and exc.status in {403, 404}:
        logger.warning(log_msg)
    elif level >= logging.ERROR:
        logger.log(level, log_msg, exc_info=exc_info)
    else:
        logger.log(level, log_msg)
    return summary


async def safe_channel_send(
    channel: discord.abc.Messageable,
    content: str,
    *,
    logger: logging.Logger,
    context: str = "channel.send",
    **send_kwargs: Any,
) -> bool:
    """Send a message; return False and log on Discord failure."""
    try:
        await channel.send(content, **send_kwargs)
        return True
    except discord.DiscordException as exc:
        channel_id = getattr(channel, "id", None)
        log_discord_error(
            logger,
            context,
            exc,
            channel_id=channel_id,
        )
        return False
