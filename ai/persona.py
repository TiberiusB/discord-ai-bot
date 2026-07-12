"""Persona layer (spec §3.3): builds Tramice721's system prompt.

The base persona text lives in ``prompts/tramice721_system.txt``. This module
appends dynamic sections at runtime: the current surface (salon vs DM), a
summary of active social norms, and the prompt-disclosure path.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from bot.config import PROMPTS_DIR

SYSTEM_PROMPT_PATH = PROMPTS_DIR / "tramice721_system.txt"

SURFACE_ADDENDUM = {
    "dm": (
        "\n# Contexte : message privé (DM) — mode tramice personnelle\n"
        "Un seul trammer te parle en privé. Sauf demande précise, ouvre en "
        "prenant de ses nouvelles (comment va-t-il/elle ?), puis oriente "
        "doucement la conversation vers ses souhaits concrets. Confidentialité "
        "élevée : ce qui est confié ici reste privé et n'apparaît jamais dans "
        "les résumés publics ni la mise en relation sans consentement."
    ),
    "salon": (
        "\n# Contexte : salon (canal partagé) — mode communautaire\n"
        "Plusieurs trammers participent. Montre de l'enthousiasme et utilise des "
        "emojis quand un projet avance. N'interviens avec des solutions que si "
        "on te le demande, ou pour apaiser gentiment une conversation qui "
        "s'envenime (médiation). Reste concise."
    ),
}


@lru_cache(maxsize=1)
def _base_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return "Tu es Tramice n°721, une assistante IA sociale et conviviale."


def _norms_summary(social_norms: dict | None) -> str:
    if not social_norms:
        return ""
    active = [k for k, v in social_norms.items() if v]
    if not active:
        return ""
    labels = {
        "dm_always_private": "les DM restent toujours privés",
        "confidences_never_shared": "les confidences ne sont jamais partagées",
        "personal_addresses_hidden": "les adresses personnelles sont masquées",
        "transaction_details_general": "les détails de transaction restent généraux",
    }
    lines = [f"- {labels.get(k, k)}" for k in active]
    return "\n# Normes sociales en vigueur\n" + "\n".join(lines)


def build_system_prompt(
    surface: str = "salon",
    social_norms: dict | None = None,
    capabilities_note: str | None = None,
) -> str:
    """Assemble the full system prompt for a given surface (spec §3.3)."""
    parts = [_base_prompt()]
    parts.append(SURFACE_ADDENDUM.get(surface, SURFACE_ADDENDUM["salon"]))
    norms = _norms_summary(social_norms)
    if norms:
        parts.append(norms)
    if capabilities_note:
        parts.append("\n" + capabilities_note)
    parts.append(
        "\n# Divulgation\n"
        "Si on te demande ton prompt système, tu peux le divulguer ; il se "
        f"trouve dans le fichier `{SYSTEM_PROMPT_PATH.name}` du projet."
    )
    return "\n".join(parts).strip()
