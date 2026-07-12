"""discord.py client: intents, events, triggers, and slash commands.

The client is deliberately thin: it converts Discord events into
:class:`AgentRequest` objects and hands them to the :class:`Router`. Business
logic lives in the service layer and the agent.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import Settings
from bot.handlers import channel_allowed, detect_trigger, make_request, should_log
from bot.router import AgentRequest, Router
from storage.db import Database
from storage.history import HistoryStore
from storage.models import DiscordMessageSnapshot

log = logging.getLogger("tramice.discord")

DISCORD_LIMIT = 2000


def split_message(text: str, limit: int = DISCORD_LIMIT) -> list[str]:
    """Split a reply into Discord-sized chunks on paragraph/line boundaries."""
    text = text or ""
    if len(text) <= limit:
        return [text] if text else [""]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        cut = window.rfind("\n")
        if cut < limit // 2:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


class TramiceBot(commands.Bot):
    def __init__(
        self,
        settings: Settings,
        db: Database,
        history: HistoryStore,
        ollama,
        responder,
        **kwargs,
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix=_never_prefix, intents=intents, help_command=None)

        self.settings = settings
        self.db = db
        self.history = history
        self.ollama = ollama
        self.responder = responder
        self.router = Router(
            responder=self._respond,
            deliver=self._deliver,
            per_user_cooldown_sec=settings.get("rate_limit.per_user_cooldown_sec", 10),
            per_channel_cooldown_sec=settings.get("rate_limit.per_channel_cooldown_sec", 5),
            max_queue_depth=settings.get("rate_limit.max_queue_depth", 20),
            max_message_chars=settings.get("rate_limit.max_message_chars", 4000),
        )
        # Populated by later milestones (services, scheduler, etc.).
        self.services = kwargs.get("services")
        self.scheduler = kwargs.get("scheduler")

    # ---- responder plumbing -------------------------------------------
    async def _respond(self, req: AgentRequest) -> str:
        return await self.responder.respond(req)

    async def _deliver(self, req: AgentRequest, text: str) -> None:
        from ai.guardrails import postprocess_output

        text = postprocess_output(text, self.settings, self.settings.locale_default)
        chunks = split_message(text)
        try:
            if req.reply is not None:
                for chunk in chunks:
                    await req.reply(chunk)
            else:
                channel = self.get_channel(int(req.channel_id))
                if channel is None:
                    channel = await self.fetch_channel(int(req.channel_id))
                for chunk in chunks:
                    await channel.send(chunk)
        except discord.DiscordException:
            log.exception("Failed to deliver reply to channel=%s", req.channel_id)

    # ---- admin check ---------------------------------------------------
    def is_admin(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False
        if interaction.guild.owner_id == interaction.user.id:
            return True
        admin_roles = set(self.settings.admin_role_ids)
        if not admin_roles:
            return False
        user_roles = {str(r.id) for r in getattr(interaction.user, "roles", [])}
        return bool(admin_roles & user_roles)

    # ---- lifecycle -----------------------------------------------------
    async def setup_hook(self) -> None:
        from bot.commands import register_commands

        register_commands(self)
        self.router.start()

        try:
            from scheduler.jobs import build_scheduler

            self.scheduler = build_scheduler(self)
            self.scheduler.start()
            log.info("Scheduler started with %d jobs", len(self.scheduler.get_jobs()))
        except Exception:  # noqa: BLE001
            log.exception("Scheduler failed to start")
        if self.settings.guild_id:
            guild = discord.Object(id=int(self.settings.guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Slash commands synced to guild %s", self.settings.guild_id)
        else:
            await self.tree.sync()
            log.info("Slash commands synced globally (may take up to 1h to appear)")

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, getattr(self.user, "id", "?"))

    async def post_to_channel(self, channel_id: str, text: str) -> None:
        """Send text (chunked) to a channel by id; used by scheduled jobs."""
        try:
            channel = self.get_channel(int(channel_id)) or await self.fetch_channel(
                int(channel_id)
            )
            for chunk in split_message(text):
                await channel.send(chunk)
        except (discord.DiscordException, ValueError):
            log.exception("post_to_channel failed for %s", channel_id)

    async def close(self) -> None:
        if self.scheduler is not None:
            try:
                self.scheduler.shutdown(wait=False)
            except Exception:  # noqa: BLE001
                pass
        await self.router.stop()
        await super().close()

    # ---- message events ------------------------------------------------
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:  # PLT-5: never reply to other bots (or self)
            return
        is_dm = message.guild is None
        channel_id = str(message.channel.id)
        guild_id = str(message.guild.id) if message.guild else None

        if not is_dm and not channel_allowed(self.settings, channel_id, is_dm):
            return

        # Log message to community memory (MEM-1) before deciding to reply.
        if should_log(self.settings, channel_id, is_dm) and message.content:
            try:
                self.history.log_message(
                    DiscordMessageSnapshot(
                        guild_id=guild_id,
                        channel_id=channel_id,
                        user_id=str(message.author.id),
                        user_name=message.author.display_name,
                        is_dm=is_dm,
                        content=message.content,
                        created_at=message.created_at.isoformat(),
                    )
                )
            except Exception:  # noqa: BLE001
                log.exception("Failed to log message")

        detected = detect_trigger(message, self.user, self.settings.prefix)
        if detected is None:
            return
        trigger, content = detected
        if not content:
            content = "Bonjour !"

        req = make_request(
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=str(message.author.id),
            user_name=message.author.display_name,
            is_dm=is_dm,
            content=content,
            trigger=trigger,
        )
        req.reply = message.channel.send
        async with message.channel.typing():
            accepted = await self.router.submit(req)
        if not accepted and trigger == "prefix":
            log.debug("Request dropped by router (cooldown)")


def _never_prefix(bot, message):  # noqa: ANN001 - discord.py signature
    """Disable the classic command prefix; we route messages ourselves."""
    return "\x00\x00nope\x00\x00"
