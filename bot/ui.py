"""Reusable Discord UI components.

``ConfirmView`` implements the confirmation pattern (spec §7.3) for mutating
game/governance actions: the bot proposes, a human confirms (NFR-1, GOV-2).
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

import discord

from bot.discord_errors import log_discord_error

log = logging.getLogger("tramice.ui")

OnConfirm = Callable[[discord.Interaction], Awaitable[None]]
OnModelPick = Callable[[discord.Interaction, str], Awaitable[None]]

CONFIRM_FAIL_MESSAGE = (
    "La confirmation a échoué. Réessaie ou contacte un admin si le problème persiste."
)

MODEL_RESET_VALUE = "__reset__"
_MAX_SELECT_OPTIONS = 25


def build_model_select_options(
    models: list[str],
    *,
    current: str | None = None,
    include_reset: bool = False,
    default_label: str | None = None,
) -> list[discord.SelectOption]:
    """Build Select options for Ollama chat models (Discord max 25)."""
    options: list[discord.SelectOption] = []
    if include_reset:
        options.append(
            discord.SelectOption(
                label="defaut — modèle de la communauté",
                value=MODEL_RESET_VALUE,
                description=(default_label or "revenir au défaut")[:100],
                emoji="↩️",
            )
        )
    slots = _MAX_SELECT_OPTIONS - len(options)
    for name in models[:slots]:
        label = name if len(name) <= 100 else name[:97] + "..."
        desc = None
        if current and name == current:
            desc = "actuellement sélectionné"
        options.append(
            discord.SelectOption(label=label, value=name, description=desc)
        )
    return options


class ModelSelectView(discord.ui.View):
    """Dropdown picker for Ollama chat models (/model, /modele)."""

    def __init__(
        self,
        *,
        author_id: int,
        models: list[str],
        body: str,
        on_pick: OnModelPick,
        current: str | None = None,
        include_reset: bool = False,
        default_label: str | None = None,
        placeholder: str = "Choisir un modèle…",
        timeout: float = 120.0,
    ):
        super().__init__(timeout=timeout)
        self._author_id = author_id
        self._body = body
        self._on_pick = on_pick
        options = build_model_select_options(
            models,
            current=current,
            include_reset=include_reset,
            default_label=default_label,
        )
        if options:
            select = discord.ui.Select(
                placeholder=placeholder,
                options=options,
                min_values=1,
                max_values=1,
            )
            select.callback = self._on_select  # type: ignore[assignment]
            self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self._author_id:
            await interaction.response.send_message(
                "Ce menu ne t'est pas destiné.", ephemeral=True
            )
            return False
        return True

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        log_discord_error(
            log,
            "ModelSelectView interaction error",
            error,
            event="model_select_view",
            user_id=interaction.user.id,
        )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(CONFIRM_FAIL_MESSAGE, ephemeral=True)
            else:
                await interaction.response.send_message(
                    CONFIRM_FAIL_MESSAGE, ephemeral=True
                )
        except discord.DiscordException as exc:
            log_discord_error(log, "ModelSelectView error response failed", exc)

    async def _on_select(self, interaction: discord.Interaction) -> None:
        assert isinstance(interaction.data, dict)
        values = interaction.data.get("values") or []
        if not values:
            await interaction.response.send_message(
                "Aucun modèle sélectionné.", ephemeral=True
            )
            return
        choice = values[0]
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        await interaction.response.edit_message(content=self._body, view=self)
        try:
            await self._on_pick(interaction, choice)
        except Exception as exc:  # noqa: BLE001
            log_discord_error(
                log,
                "ModelSelectView on_pick failed",
                exc,
                event="model_select_view.on_pick",
                user_id=interaction.user.id,
            )
            try:
                await interaction.followup.send(CONFIRM_FAIL_MESSAGE, ephemeral=True)
            except discord.DiscordException as send_exc:
                log_discord_error(log, "ModelSelectView failure notice failed", send_exc)
        self.stop()


class ConfirmView(discord.ui.View):
    def __init__(self, author_id: int, on_confirm: OnConfirm, timeout: float = 120.0):
        super().__init__(timeout=timeout)
        self._author_id = author_id
        self._on_confirm = on_confirm
        self.value: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self._author_id:
            await interaction.response.send_message(
                "Seule la personne à l'origine de la demande peut confirmer.",
                ephemeral=True,
            )
            return False
        return True

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        log_discord_error(
            log,
            "ConfirmView interaction error",
            error,
            event="confirm_view",
            user_id=interaction.user.id,
            item=getattr(item, "label", type(item).__name__),
        )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(CONFIRM_FAIL_MESSAGE, ephemeral=True)
            else:
                await interaction.response.send_message(
                    CONFIRM_FAIL_MESSAGE, ephemeral=True
                )
        except discord.DiscordException as exc:
            log_discord_error(log, "ConfirmView error response failed", exc)

    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        await interaction.response.edit_message(view=self)
        try:
            await self._on_confirm(interaction)
        except Exception as exc:  # noqa: BLE001
            log_discord_error(
                log,
                "ConfirmView on_confirm failed",
                exc,
                event="confirm_view.on_confirm",
                user_id=interaction.user.id,
            )
            try:
                await interaction.followup.send(CONFIRM_FAIL_MESSAGE, ephemeral=True)
            except discord.DiscordException as send_exc:
                log_discord_error(log, "ConfirmView failure notice failed", send_exc)
        self.stop()

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        await interaction.response.edit_message(content="Annulé. 🌙", view=self)
        self.stop()
