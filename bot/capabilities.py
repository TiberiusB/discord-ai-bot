"""Discord capability scanner and communication strategy (post-MVP).

Introspects the bot's guild + channel permissions at launch and on a schedule,
writes ``data/capabilities.json``, and builds a French note for the agent prompt.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord

from bot.discord_errors import log_discord_error

if TYPE_CHECKING:
    from bot.discord_client import TramiceBot

log = logging.getLogger("tramice.capabilities")

PERM_FLAGS: dict[str, str] = {
    "send_messages": "send_messages",
    "send_tts_messages": "send_tts_messages",
    "create_public_threads": "create_public_threads",
    "create_private_threads": "create_private_threads",
    "manage_events": "manage_events",
    "mention_everyone": "mention_everyone",
    "manage_messages": "manage_messages",
    "use_external_emojis": "use_external_emojis",
    "use_soundboard": "use_soundboard",
    "connect": "connect",
    "speak": "speak",
    "embed_links": "embed_links",
    "attach_files": "attach_files",
}


def capabilities_path(settings) -> Path:
    return settings.data_dir / "capabilities.json"


def _perm_dict(perms: discord.Permissions) -> dict[str, bool]:
    return {key: bool(getattr(perms, attr, False)) for key, attr in PERM_FLAGS.items()}


def _strategy_for(perms: dict[str, bool]) -> dict[str, str]:
    """Map raw permissions to communication guidance."""
    return {
        "send_messages": "oui" if perms.get("send_messages") else "non — rester silencieuse",
        "tts": "oui (/say)" if perms.get("send_tts_messages") else "non",
        "threads": (
            "oui"
            if perms.get("create_public_threads") or perms.get("create_private_threads")
            else "non"
        ),
        "scheduled_events": "oui" if perms.get("manage_events") else "non",
        "mention_everyone": (
            "éviter sauf urgence et permission explicite"
            if perms.get("mention_everyone")
            else "jamais"
        ),
        "slowmode_bypass": "oui" if perms.get("manage_messages") else "respecter le slow mode",
        "soundboard": "oui (/son)" if perms.get("use_soundboard") else "non",
        "external_emoji": "oui" if perms.get("use_external_emojis") else "emojis du serveur seulement",
        "voice": "oui" if perms.get("connect") else "non",
    }


def build_strategy(guild_perms: dict[str, bool], channels: dict[str, dict]) -> dict[str, Any]:
    base = _strategy_for(guild_perms)
    thread_channels = [
        cid for cid, p in channels.items()
        if p.get("create_public_threads") or p.get("create_private_threads")
    ]
    base["thread_channels"] = thread_channels
    return base


def build_capabilities_note(snapshot: dict[str, Any] | None) -> str:
    if not snapshot or not snapshot.get("guild_id"):
        return (
            "\n# Capacités Discord\n"
            "Aucun serveur configuré (GUILD_ID manquant). Agis uniquement en DM."
        )
    strategy = snapshot.get("strategy") or {}
    gp = snapshot.get("guild_permissions") or {}
    lines = [
        "\n# Capacités Discord et stratégie de communication",
        f"Dernière analyse : {snapshot.get('scanned_at', '?')}",
        f"- Envoyer des messages : {strategy.get('send_messages', '?')}",
        f"- Synthèse vocale (TTS) : {strategy.get('tts', '?')}",
        f"- Créer des fils : {strategy.get('threads', '?')}",
        f"- Événements planifiés Discord : {strategy.get('scheduled_events', '?')}",
        f"- @everyone : {strategy.get('mention_everyone', '?')}",
        f"- Slow mode : {strategy.get('slowmode_bypass', '?')}",
        f"- Soundboard : {strategy.get('soundboard', '?')}",
        f"- Emojis externes : {strategy.get('external_emoji', '?')}",
        f"- Salon vocal : {strategy.get('voice', '?')}",
    ]
    tch = strategy.get("thread_channels") or []
    if tch:
        lines.append(f"- Salons autorisés pour fils : {', '.join(tch)}")
    if not gp.get("send_messages"):
        lines.append("- ATTENTION : pas de permission SEND_MESSAGES au niveau serveur.")
    return "\n".join(lines)


def load_capabilities_snapshot(settings) -> dict[str, Any]:
    path = capabilities_path(settings)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        log.warning("Could not read capabilities snapshot")
        return {}


def save_capabilities_snapshot(settings, snapshot: dict[str, Any]) -> None:
    path = capabilities_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")


def can(snapshot: dict[str, Any] | None, permission: str, channel_id: str | None = None) -> bool:
    """Check a permission from the cached snapshot."""
    if not snapshot:
        return False
    if channel_id:
        ch = (snapshot.get("channels") or {}).get(str(channel_id), {})
        if permission in ch:
            return bool(ch[permission])
    gp = snapshot.get("guild_permissions") or {}
    return bool(gp.get(permission))


async def scan_capabilities(bot: "TramiceBot") -> dict[str, Any]:
    """Scan guild + allowlisted channel permissions; persist snapshot."""
    settings = bot.settings
    guild_id = settings.guild_id
    if not guild_id:
        snapshot = {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "guild_id": None,
            "guild_permissions": {},
            "channels": {},
            "strategy": {},
        }
        save_capabilities_snapshot(settings, snapshot)
        return snapshot

    guild = bot.get_guild(int(guild_id))
    if guild is None:
        try:
            guild = await bot.fetch_guild(int(guild_id))
        except discord.DiscordException as exc:
            log_discord_error(
                log, "capability scan: guild unreachable", exc, guild_id=guild_id
            )
            return load_capabilities_snapshot(settings)

    me = guild.me
    if me is None:
        try:
            me = await guild.fetch_member(bot.user.id)  # type: ignore[union-attr]
        except discord.DiscordException:
            log.warning("capability scan: could not resolve bot member")
            return load_capabilities_snapshot(settings)

    guild_perms = _perm_dict(me.guild_permissions)
    channels: dict[str, dict[str, bool]] = {}
    allowlist = settings.get("channels.interact_allowlist", []) or settings.get(
        "channels.allowlist", []
    ) or []
    log_allowlist = settings.get("channels.log_allowlist", []) or allowlist
    channel_ids = set(str(c) for c in allowlist) | set(str(c) for c in log_allowlist)
    for cid in channel_ids:
        try:
            channel = guild.get_channel(int(cid)) or await bot.fetch_channel(int(cid))
        except (discord.DiscordException, ValueError):
            continue
        if hasattr(channel, "permissions_for"):
            channels[str(cid)] = _perm_dict(channel.permissions_for(me))  # type: ignore[arg-type]

    member_count = guild.member_count
    if member_count is None:
        member_count = len(guild.members) if guild.members else 0
    roles = [{"id": str(r.id), "name": r.name} for r in guild.roles if r.name != "@everyone"]
    snapshot = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "guild_id": str(guild.id),
        "guild_name": guild.name,
        "member_count": member_count,
        "channel_count": len(guild.channels),
        "roles": roles[:50],
        "guild_permissions": guild_perms,
        "channels": channels,
        "strategy": build_strategy(guild_perms, channels),
    }
    save_capabilities_snapshot(settings, snapshot)
    log.info("Capability scan complete for guild %s (%d channels)", guild.id, len(channels))
    return snapshot


def capabilities_signature(settings) -> str:
    snap = load_capabilities_snapshot(settings)
    return str(snap.get("scanned_at", ""))
