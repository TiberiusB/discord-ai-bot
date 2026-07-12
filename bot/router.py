"""Message router (spec §3.1): rate limiting + single-flight LLM queue.

Ollama serves one inference at a time on the target hardware, so all agent work
is funnelled through a bounded async queue processed by a single worker. Per-user
and per-channel cooldowns protect against flooding.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Literal, Optional

log = logging.getLogger("tramice.router")

Surface = Literal["salon", "dm"]
Trigger = Literal["prefix", "mention", "slash"]

BUSY_MESSAGE = "Je suis un peu débordée en ce moment — réessaie dans un instant."


@dataclass
class AgentRequest:
    guild_id: str | None
    channel_id: str
    user_id: str
    surface: Surface
    thread_id: str
    content: str
    trigger: Trigger
    command: str | None = None
    user_name: str | None = None
    # Per-request delivery callback (set by the Discord layer). Slash commands
    # reply via ``interaction.followup``; messages via ``channel.send``.
    reply: Optional[Callable[[str], Awaitable[None]]] = field(
        default=None, repr=False, compare=False
    )


# A responder turns a request into a text reply. Deliver sends text to Discord.
Responder = Callable[[AgentRequest], Awaitable[str]]
Deliver = Callable[[AgentRequest, str], Awaitable[None]]


class Router:
    def __init__(
        self,
        responder: Responder,
        deliver: Deliver,
        *,
        per_user_cooldown_sec: float = 10.0,
        per_channel_cooldown_sec: float = 5.0,
        max_queue_depth: int = 20,
        max_message_chars: int = 4000,
    ):
        self._responder = responder
        self._deliver = deliver
        self.per_user_cooldown = per_user_cooldown_sec
        self.per_channel_cooldown = per_channel_cooldown_sec
        self.max_message_chars = max_message_chars

        self._queue: asyncio.Queue[AgentRequest] = asyncio.Queue(maxsize=max_queue_depth)
        self._last_user: dict[str, float] = {}
        self._last_channel: dict[str, float] = {}
        self._worker: asyncio.Task | None = None

    def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._run(), name="router-worker")
            log.info("Router worker started")

    async def stop(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None

    def _cooldown_ok(self, req: AgentRequest) -> bool:
        now = time.monotonic()
        # Slash commands bypass cooldown (structured, user-initiated intent).
        if req.trigger == "slash":
            return True
        last_u = self._last_user.get(req.user_id, 0.0)
        if now - last_u < self.per_user_cooldown:
            return False
        if req.surface == "salon":
            last_c = self._last_channel.get(req.channel_id, 0.0)
            if now - last_c < self.per_channel_cooldown:
                return False
        self._last_user[req.user_id] = now
        self._last_channel[req.channel_id] = now
        return True

    async def submit(self, req: AgentRequest) -> bool:
        """Enqueue a request. Returns False if dropped (cooldown or full queue)."""
        if len(req.content) > self.max_message_chars:
            req.content = req.content[: self.max_message_chars] + " […]"
        if not self._cooldown_ok(req):
            log.debug("Cooldown drop for user=%s channel=%s", req.user_id, req.channel_id)
            return False
        try:
            self._queue.put_nowait(req)
        except asyncio.QueueFull:
            await self._deliver(req, BUSY_MESSAGE)
            return False
        return True

    async def _run(self) -> None:
        while True:
            req = await self._queue.get()
            try:
                reply = await self._responder(req)
                if reply:
                    await self._deliver(req, reply)
            except Exception:  # noqa: BLE001 - one bad turn must not kill the worker
                log.exception("Responder failed for thread=%s", req.thread_id)
                await self._deliver(
                    req,
                    "Oups, une petite turbulence de mon côté. Peux-tu reformuler ?",
                )
            finally:
                self._queue.task_done()
