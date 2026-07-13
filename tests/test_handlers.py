"""Tests for channel policy (allowlist mode)."""

from bot.config import Settings
from bot.handlers import channel_allowed, should_log


def test_allowlist_permits_configured_channel(settings: Settings) -> None:
    assert channel_allowed(settings, "111", is_dm=False) is True


def test_allowlist_blocks_unknown_channel(settings: Settings) -> None:
    assert channel_allowed(settings, "222", is_dm=False) is False


def test_allowlist_empty_blocks_salons() -> None:
    s = Settings(raw={"channels": {"log_mode": "allowlist", "allowlist": []}})
    assert channel_allowed(s, "111", is_dm=False) is False


def test_dm_always_allowed(settings: Settings) -> None:
    assert channel_allowed(settings, "999", is_dm=True) is True


def test_should_log_dm_even_when_not_in_allowlist() -> None:
    s = Settings(raw={"channels": {"log_mode": "allowlist", "allowlist": []}})
    assert should_log(s, "111", is_dm=True) is True
