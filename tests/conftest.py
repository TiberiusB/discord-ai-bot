"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bot.config import Settings, PROJECT_ROOT


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    raw = {
        "bot": {"prefix": "!ai", "locale_default": "fr", "timezone": "America/Montreal"},
        "channels": {
            "log_mode": "allowlist",
            "allowlist": ["111"],
            "denylist": ["999"],
        },
        "rate_limit": {
            "per_user_cooldown_sec": 10,
            "per_channel_cooldown_sec": 5,
            "max_queue_depth": 5,
            "max_message_chars": 4000,
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(raw), encoding="utf-8")
    return Settings(
        raw=raw,
        discord_token="test-token",
        data_dir=tmp_path / "data",
        project_root=PROJECT_ROOT,
        docs_dir=PROJECT_ROOT / "docs",
        prompts_dir=PROJECT_ROOT / "prompts",
    )
