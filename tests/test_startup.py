"""Tests for startup validation warnings."""

from bot.config import Settings
from bot.startup import validate_launch_config


def test_empty_allowlist_warns() -> None:
    s = Settings(raw={"channels": {"log_mode": "allowlist", "allowlist": []}})
    warnings = validate_launch_config(s)
    assert any("allowlist is empty" in w for w in warnings)


def test_log_mode_all_warns() -> None:
    s = Settings(raw={"channels": {"log_mode": "all", "allowlist": []}})
    warnings = validate_launch_config(s)
    assert any("log_mode is 'all'" in w for w in warnings)
