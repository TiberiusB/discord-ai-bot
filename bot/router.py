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
from enum import Enum
from typing import Awaitable, Callable, Literal, Optional

log = logging.getLogger("tramice.router")

Surface = Literal["salon", "dm"]
Trigger = Literal["prefix", "mention", "slash"]

BUSY_MESSAGE = "Je suis un peu débordée en ce moment — réessaie dans un instant."
COOLDOWN_USER_MESSAGE = (
    "Patience — laisse-moi quelques secondes pour reprendre mon souffle, "
    "puis réessaie. 🌿"
)
COOLDOWN_CHANNEL_MESSAGE = (
    "Ce salon est un peu pressé en ce moment — réessaie dans un instant."
)


class SubmitStatus(str, Enum):
    ACCEPTED = "accepted"
    COOLDOWN_USER = "cooldown_user"
    COOLDOWN_CHANNEL = "cooldown_channel"
    QUEUE_FULL = "queue_full"


@dataclass
class SubmitResult:
    status: SubmitStatus
    message: str | None = None


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

        self._queue: asyncio.Queue[AgentRequest | None] = asyncio.Queue(
            maxsize=max_queue_depth
        )
        self._last_user: dict[str, float] = {}
        self._last_channel: dict[str, float] = {}
        self._worker: asyncio.Task | None = None
        self._stopping = False

    def start(self) -> None:
        if self._worker is None:
            self._stopping = False
            self._worker = asyncio.create_task(self._run(), name="router-worker")
            log.info("Router worker started")

    async def stop(self, *, drain_timeout: float = 30.0) -> None:
        """Drain pending work, then stop the worker."""
        if self._worker is None:
            return
        self._stopping = True
        try:
            self._queue.put_nowait(None)
        except asyncio.QueueFull:
            pass
        try:
            await asyncio.wait_for(self._queue.join(), timeout=drain_timeout)
        except asyncio.TimeoutError:
            pending = self._queue.qsize()
            log.warning("Router drain timed out (%d items may be dropped)", pending)
        self._worker.cancel()
        try:
            await self._worker
        except asyncio.CancelledError:
            pass
        self._worker = None

    def _check_cooldown(self, req: AgentRequest) -> SubmitStatus | None:
        now = time.monotonic()
        if req.trigger == "slash":
            return None
        last_u = self._last_user.get(req.user_id, 0.0)
        if now - last_u < self.per_user_cooldown:
            return SubmitStatus.COOLDOWN_USER
        if req.surface == "salon":
            last_c = self._last_channel.get(req.channel_id, 0.0)
            if now - last_c < self.per_channel_cooldown:
                return SubmitStatus.COOLDOWN_CHANNEL
        return None

    def _mark_cooldown(self, req: AgentRequest) -> None:
        now = time.monotonic()
        self._last_user[req.user_id] = now
        if req.surface == "salon":
            self._last_channel[req.channel_id] = now

    async def submit(self, req: AgentRequest) -> SubmitResult:
        """Enqueue a request. Returns status if dropped (cooldown or full queue)."""
        if len(req.content) > self.max_message_chars:
            req.content = req.content[: self.max_message_chars] + " […]"

        cooldown = self._check_cooldown(req)
        if cooldown is not None:
            log.debug(
                "Cooldown drop user=%s channel=%s reason=%s",
                req.user_id,
                req.channel_id,
                cooldown.value,
            )
            message = (
                COOLDOWN_USER_MESSAGE
                if cooldown is SubmitStatus.COOLDOWN_USER
                else COOLDOWN_CHANNEL_MESSAGE
            )
            return SubmitResult(status=cooldown, message=message)

        self._mark_cooldown(req)

        try:
            self._queue.put_nowait(req)
        except asyncio.QueueFull:
            # Caller delivers rejection messages (same as cooldown path).
            return SubmitResult(status=SubmitStatus.QUEUE_FULL, message=BUSY_MESSAGE)
        return SubmitResult(status=SubmitStatus.ACCEPTED)

    async def _run(self) -> None:
        while True:
            req = await self._queue.get()
            try:
                if req is None:
                    return
                started = time.monotonic()
                try:
                    reply = await self._responder(req)
                    if reply:
                        await self._deliver(req, reply)
                except Exception:  # noqa: BLE001 - one bad turn must not kill worker
                    log.exception("Responder failed for thread=%s", req.thread_id)
                    await self._deliver(
                        req,
                        "Oups, une petite turbulence de mon côté. Peux-tu reformuler ?",
                    )
                finally:
                    elapsed_ms = (time.monotonic() - started) * 1000
                    log.debug(
                        "Turn completed thread=%s duration_ms=%.1f",
                        req.thread_id,
                        elapsed_ms,
                    )
            finally:
                self._queue.task_done()
