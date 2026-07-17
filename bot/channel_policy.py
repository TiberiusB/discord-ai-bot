"""Channel allowlist helpers (log vs interact)."""

from __future__ import annotations

from bot.config import Settings


def _channel_set(settings: Settings, key: str) -> set[str]:
    values = settings.get(key, []) or []
    return {str(c) for c in values}


def resolve_channel_lists(settings: Settings) -> tuple[set[str], set[str]]:
    """Return (log_allowlist, interact_allowlist) with legacy fallback."""
    legacy = _channel_set(settings, "channels.allowlist")
    log_list = _channel_set(settings, "channels.log_allowlist") or legacy
    interact_list = _channel_set(settings, "channels.interact_allowlist") or legacy
    return log_list, interact_list


def channel_in_log(settings: Settings, channel_id: str, is_dm: bool) -> bool:
    if is_dm:
        return True
    mode = settings.get("channels.log_mode", "allowlist")
    denylist = _channel_set(settings, "channels.denylist")
    cid = str(channel_id)
    if cid in denylist:
        return False
    if mode == "all":
        return True
    if mode == "denylist":
        return True
    log_list, _ = resolve_channel_lists(settings)
    if not log_list:
        return False
    return cid in log_list


def channel_in_interact(settings: Settings, channel_id: str, is_dm: bool) -> bool:
    if is_dm:
        return True
    mode = settings.get("channels.log_mode", "allowlist")
    denylist = _channel_set(settings, "channels.denylist")
    cid = str(channel_id)
    if cid in denylist:
        return False
    if mode == "all":
        return True
    if mode == "denylist":
        return True
    _, interact_list = resolve_channel_lists(settings)
    if not interact_list:
        return False
    return cid in interact_list
