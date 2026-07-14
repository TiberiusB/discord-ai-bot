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
from bot.discord_errors import log_discord_error, safe_channel_send
from bot.handlers import channel_allowed, detect_trigger, make_request, should_log
from bot.observability import get_runtime_health, touch_health
from bot.router import AgentRequest, Router, SubmitStatus
from storage.db import Database
from storage.history import HistoryStore
from storage.models import DiscordMessageSnapshot

log = logging.getLogger("tramice.discord")

DISCORD_LIMIT = 2000
COMMAND_ERROR_MESSAGE = (
    "Oups, cette commande a rencontré une petite turbulence. "
    "Réessaie dans un instant ou contacte un admin si ça persiste."
)


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
        except discord.DiscordException as exc:
            log_discord_error(
                log,
                "Failed to deliver reply",
                exc,
                channel_id=req.channel_id,
                user_id=req.user_id,
            )

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
        except Exception as exc:  # noqa: BLE001
            log.exception("Scheduler failed to start")
            from bot.observability import record_event_error

            record_event_error("setup_hook.scheduler", str(exc))
        if self.settings.guild_id:
            guild = discord.Object(id=int(self.settings.guild_id))
            self.tree.copy_global_to(guild=guild)
            try:
                await self.tree.sync(guild=guild)
                log.info("Slash commands synced to guild %s", self.settings.guild_id)
            except discord.DiscordException as exc:
                log_discord_error(
                    log,
                    "Slash command guild sync failed",
                    exc,
                    event="setup_hook.sync_guild",
                    guild_id=self.settings.guild_id,
                )
        else:
            try:
                await self.tree.sync()
                log.info("Slash commands synced globally (may take up to 1h to appear)")
            except discord.DiscordException as exc:
                log_discord_error(
                    log,
                    "Slash command global sync failed",
                    exc,
                    event="setup_hook.sync_global",
                )

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, getattr(self.user, "id", "?"))
        touch_health()
        try:
            from bot.capabilities import scan_capabilities

            await scan_capabilities(self)
        except Exception as exc:  # noqa: BLE001
            log.exception("Initial capability scan failed")
            from bot.observability import record_event_error

            record_event_error("on_ready.capability_scan", str(exc))

    async def on_error(self, event_method: str, /, *args, **kwargs) -> None:
        import sys

        exc = sys.exc_info()[1]
        if exc is None:
            log.error("Event handler error in %s (no exception info)", event_method)
            return
        log_discord_error(
            log,
            f"Unhandled event handler error in {event_method}",
            exc,
            event=event_method,
            exc_info=exc,
        )

    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.display_name == after.display_name:
            return
        identity = getattr(self.services, "identity", None) if self.services else None
        if identity is None:
            return
        try:
            identity.record_alias(str(after.id), after.display_name)
        except Exception:  # noqa: BLE001
            log.exception("Failed to record member alias for %s", after.id)

    async def on_user_update(self, before: discord.User, after: discord.User) -> None:
        if before.display_name == after.display_name:
            return
        identity = getattr(self.services, "identity", None) if self.services else None
        if identity is None:
            return
        try:
            identity.record_alias(str(after.id), after.display_name)
        except Exception:  # noqa: BLE001
            log.exception("Failed to record user alias for %s", after.id)

    async def dm_admins(self, guild_id: str, text: str) -> int:
        """DM guild owner and admin-role members. Returns count of DMs sent."""
        try:
            guild = self.get_guild(int(guild_id)) or await self.fetch_guild(int(guild_id))
        except (discord.DiscordException, ValueError) as exc:
            log_discord_error(log, "dm_admins: guild unreachable", exc, guild_id=guild_id)
            return 0

        recipients: set[int] = set()
        if guild.owner_id is not None:
            recipients.add(guild.owner_id)
        admin_roles = {int(r) for r in self.settings.admin_role_ids if r.isdigit()}
        if admin_roles:
            for member in guild.members:
                if any(r.id in admin_roles for r in member.roles):
                    recipients.add(member.id)

        sent = 0
        for uid in recipients:
            if uid == self.user.id:  # type: ignore[union-attr]
                continue
            try:
                user = guild.get_member(uid) or await self.fetch_user(uid)
                await user.send(text[:2000])
                sent += 1
            except discord.DiscordException as exc:
                log_discord_error(
                    log, "Could not DM admin user", exc, user_id=uid, guild_id=guild_id
                )
        return sent

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        from bot.discord_errors import describe_discord_error

        cmd = getattr(interaction.command, "name", "?")
        uid = getattr(interaction.user, "id", "?")
        summary = describe_discord_error(error)
        log.error(
            "Slash command error command=%s user=%s — %s",
            cmd,
            uid,
            summary,
            exc_info=error,
        )
        from bot.observability import record_event_error

        record_event_error(f"slash:{cmd}", summary)
        try:
            if interaction.response.is_done():
                await interaction.followup.send(COMMAND_ERROR_MESSAGE, ephemeral=True)
            else:
                await interaction.response.send_message(
                    COMMAND_ERROR_MESSAGE, ephemeral=True
                )
        except discord.DiscordException as exc:
            log_discord_error(
                log,
                "Failed to send command error response",
                exc,
                command=cmd,
                user_id=uid,
            )

    def health_snapshot_lines(self) -> list[str]:
        """Build Discord/runtime lines for /health."""
        from bot.capabilities import load_capabilities_snapshot

        snap = load_capabilities_snapshot(self.settings)
        runtime = get_runtime_health()
        lines = [
            f"- Gateway : {'connecté ✅' if self.is_ready() else 'non prêt ❌'}",
        ]
        if self.latency is not None:
            lines.append(f"- Latence gateway : {round(self.latency * 1000)} ms")
        lines.append(
            f"- File router : {self.router.queue_depth} requête(s) en attente"
        )
        scanned = snap.get("scanned_at") if snap else None
        lines.append(
            f"- Dernière analyse capacités : {scanned or 'jamais'}"
        )
        if runtime["last_job_error_id"]:
            lines.append(
                f"- Dernière erreur job : `{runtime['last_job_error_id']}` "
                f"({runtime['last_job_error_at']})"
            )
        else:
            lines.append("- Dernière erreur job : aucune")
        if runtime["last_event_error"]:
            lines.append(
                f"- Dernière erreur événement : {runtime['last_event_error']} "
                f"({runtime['last_event_error_at']})"
            )
        else:
            lines.append("- Dernière erreur événement : aucune")
        if runtime["event_error_count"] or runtime["job_error_count"]:
            lines.append(
                f"- Compteurs erreurs : {runtime['event_error_count']} événement(s), "
                f"{runtime['job_error_count']} job(s)"
            )
        return lines

    async def post_to_channel(self, channel_id: str, text: str) -> None:
        """Send text (chunked) to a channel by id; used by scheduled jobs."""
        try:
            channel = self.get_channel(int(channel_id)) or await self.fetch_channel(
                int(channel_id)
            )
            for chunk in split_message(text):
                await channel.send(chunk)
        except (discord.DiscordException, ValueError) as exc:
            log_discord_error(
                log, "post_to_channel failed", exc, channel_id=channel_id
            )

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
                identity = getattr(self.services, "identity", None) if self.services else None
                if identity is not None:
                    identity.record_alias(str(message.author.id), message.author.display_name)
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
        try:
            async with message.channel.typing():
                result = await self.router.submit(req)
            if result.status is not SubmitStatus.ACCEPTED and result.message:
                await safe_channel_send(
                    message.channel,
                    result.message,
                    logger=log,
                    context="on_message.rejection",
                )
        except discord.DiscordException as exc:
            log_discord_error(
                log,
                "on_message handler failed",
                exc,
                event="on_message",
                channel_id=channel_id,
                user_id=str(message.author.id),
            )


def _never_prefix(bot, message):  # noqa: ANN001 - discord.py signature
    """Disable the classic command prefix; we route messages ourselves."""
    return "\x00\x00nope\x00\x00"
