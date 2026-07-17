"""Tests for channel policy (log vs interact allowlists)."""

from bot.channel_policy import channel_in_interact, channel_in_log
from bot.config import Settings
from bot.handlers import channel_allowed, should_log


def test_interact_allowlist_permits_configured_channel(settings: Settings) -> None:
    assert channel_allowed(settings, "111", is_dm=False) is True


def test_interact_allowlist_blocks_unknown_channel(settings: Settings) -> None:
    assert channel_allowed(settings, "222", is_dm=False) is False


def test_log_includes_readonly_channel() -> None:
    s = Settings(
        raw={
            "channels": {
                "log_mode": "allowlist",
                "interact_allowlist": ["111"],
                "log_allowlist": ["111", "333"],
            }
        }
    )
    assert channel_in_interact(s, "333", False) is False
    assert channel_in_log(s, "333", False) is True
    assert should_log(s, "333", False) is True
    assert channel_allowed(s, "333", False) is False


def test_legacy_allowlist_fallback() -> None:
    s = Settings(raw={"channels": {"log_mode": "allowlist", "allowlist": ["111"]}})
    assert channel_in_interact(s, "111", False) is True
    assert channel_in_log(s, "111", False) is True


def test_dm_always_allowed(settings: Settings) -> None:
    assert channel_allowed(settings, "999", is_dm=True) is True


def test_should_log_dm_even_when_salon_lists_empty() -> None:
    s = Settings(raw={"channels": {"log_mode": "allowlist", "interact_allowlist": []}})
    assert should_log(s, "111", is_dm=True) is True
