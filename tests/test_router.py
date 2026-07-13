"""Tests for router rate limiting and submit status."""

from __future__ import annotations

import pytest

from bot.router import AgentRequest, Router, SubmitStatus


def _make_req(**kwargs):
    defaults = {
        "guild_id": "g1",
        "channel_id": "c1",
        "user_id": "u1",
        "surface": "salon",
        "thread_id": "u1-c1",
        "content": "hello",
        "trigger": "prefix",
    }
    defaults.update(kwargs)
    return AgentRequest(**defaults)


@pytest.fixture
async def router():
    replies: list[str] = []

    async def responder(req):
        return f"echo:{req.content}"

    async def deliver(_req, text):
        replies.append(text)

    r = Router(
        responder,
        deliver,
        per_user_cooldown_sec=60,
        per_channel_cooldown_sec=60,
        max_queue_depth=2,
    )
    r.start()
    yield r, replies
    await r.stop()


@pytest.mark.asyncio
async def test_submit_accepts_first_request(router) -> None:
    r, _ = router
    result = await r.submit(_make_req())
    assert result.status is SubmitStatus.ACCEPTED


@pytest.mark.asyncio
async def test_submit_cooldown_user(router) -> None:
    r, _ = router
    await r.submit(_make_req())
    result = await r.submit(_make_req())
    assert result.status is SubmitStatus.COOLDOWN_USER
    assert result.message is not None


@pytest.mark.asyncio
async def test_slash_bypasses_cooldown(router) -> None:
    r, _ = router
    await r.submit(_make_req())
    result = await r.submit(_make_req(trigger="slash"))
    assert result.status is SubmitStatus.ACCEPTED


@pytest.mark.asyncio
async def test_queue_full_returns_message_without_delivering() -> None:
    """Queue-full rejections are returned to the caller; router must not deliver."""
    delivered: list[str] = []

    async def responder(_req):
        return "never"

    async def deliver(_req, text):
        delivered.append(text)

    r = Router(responder, deliver, max_queue_depth=1)
    # Worker not started — queue stays full after first enqueue.
    await r.submit(_make_req(user_id="u1"))
    result = await r.submit(_make_req(user_id="u2", trigger="slash"))
    assert result.status is SubmitStatus.QUEUE_FULL
    assert result.message is not None
    assert delivered == []
