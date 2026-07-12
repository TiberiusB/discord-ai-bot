"""Reusable Discord UI components.

``ConfirmView`` implements the confirmation pattern (spec §7.3) for mutating
game/governance actions: the bot proposes, a human confirms (NFR-1, GOV-2).
"""

from __future__ import annotations

from typing import Awaitable, Callable

import discord

OnConfirm = Callable[[discord.Interaction], Awaitable[None]]


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

    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        await interaction.response.edit_message(view=self)
        await self._on_confirm(interaction)
        self.stop()

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        await interaction.response.edit_message(content="Annulé. 🌙", view=self)
        self.stop()
