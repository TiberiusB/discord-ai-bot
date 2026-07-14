"""Tests for Discord error classification and runtime health tracking."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import discord
import pytest

from bot.discord_client import TramiceBot
from bot.discord_errors import describe_discord_error
from bot.observability import get_runtime_health, log_job, record_event_error


def test_describe_login_failure() -> None:
    msg = describe_discord_error(discord.LoginFailure("bad token"))
    assert "DISCORD_TOKEN" in msg


def test_describe_privileged_intents() -> None:
    msg = describe_discord_error(discord.PrivilegedIntentsRequired("members"))
    assert "Intents" in msg or "intents" in msg.lower()


def test_describe_http_exception_with_code() -> None:
    response = Mock()
    response.status = 403
    exc = discord.HTTPException(response, {"message": "Missing Access", "code": 50001})
    msg = describe_discord_error(exc)
    assert "50001" in msg
    assert "403" in msg


def test_describe_forbidden() -> None:
    msg = describe_discord_error(discord.Forbidden(Mock(status=403), "nope"))
    assert "403" in msg or "Interdit" in msg


def test_record_event_and_job_errors() -> None:
    record_event_error("on_message", "send failed")
    log_job(job_id="test_job", duration_ms=1.0, status="error")
    health = get_runtime_health()
    assert health["last_event_error"] == "on_message: send failed"
    assert health["last_job_error_id"] == "test_job"
    assert health["event_error_count"] >= 1
    assert health["job_error_count"] >= 1


@pytest.mark.asyncio
async def test_dm_admins_skips_none_owner_id() -> None:
    guild = Mock()
    guild.owner_id = None
    guild.members = []

    bot = Mock()
    bot.settings = Mock(admin_role_ids=[])
    bot.user = Mock(id=999)
    bot.get_guild = Mock(return_value=guild)
    bot.fetch_user = AsyncMock()

    sent = await TramiceBot.dm_admins(bot, "123", "alert")
    assert sent == 0
    bot.fetch_user.assert_not_called()
