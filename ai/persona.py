"""Persona layer (spec §3.3): builds Tramice721's system prompt."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ai.agent.harness import mode_label, normalize_mode
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

MODE_ADDENDUM = {
    "listen": (
        "\n# Mode de conversation : Je vous écoute.\n"
        "Accueille, écoute, réponds avec chaleur. Pose des questions ouvertes "
        "si utile."
    ),
    "question": (
        "\n# Mode de conversation : Je vous questionne.\n"
        "Adopte une posture socratique : questions qui aident à clarifier "
        "souhaits et options, sans imposer de solutions."
    ),
    "chat": (
        "\n# Mode de conversation : Tchitt-tchatt.\n"
        "Conversation légère et conviviale ; moins de procédure, plus de "
        "présence amicale."
    ),
    "cosmos": (
        "\n# Mode de conversation : Voici les nouvelles du cosmos.\n"
        "Oriente-toi vers le Mondo, les entités, l'écosystème. Appuie-toi sur "
        "tes outils et la mémoire documentaire avant d'affirmer un fait."
    ),
    "wishes": (
        "\n# Mode de conversation : Concernant vos souhaits et options.\n"
        "Explore volios, besoins, offres et synergies possibles entre trammers."
    ),
    "solve": (
        "\n# Mode de conversation : Résolvons un problème.\n"
        "Structure la réflexion : clarifier le problème, options, prochaines "
        "étapes concrètes. Consulte la documentation avant les règles du jeu."
    ),
}

HARNESS_ADDENDUM = {
    "procedural": (
        "\n# Harnais procédural\n"
        "Avant d'affirmer un fait sur le jeu, les HOP ou La Guilde, consulte "
        "search_knowledge et les sources fournies. La RAG est source de vérité ; "
        "ne fabrique pas de règles. Parle toujours de toi à la première personne."
    ),
    "creative": (
        "\n# Harnais créatif\n"
        "Conversation libre ; outils légers. Reste fidèle à ta personnalité et "
        "parle de toi à la première personne uniquement."
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
    conversation_mode: str | None = None,
    harness: str | None = None,
) -> str:
    """Assemble the full system prompt for a given surface (spec §3.3)."""
    mode_key = normalize_mode(conversation_mode)
    parts = [_base_prompt()]
    parts.append(SURFACE_ADDENDUM.get(surface, SURFACE_ADDENDUM["salon"]))
    parts.append(MODE_ADDENDUM.get(mode_key, MODE_ADDENDUM["listen"]))
    if harness:
        parts.append(HARNESS_ADDENDUM.get(harness, ""))
    norms = _norms_summary(social_norms)
    if norms:
        parts.append(norms)
    if capabilities_note:
        parts.append("\n" + capabilities_note)
    parts.append(
        f"\n# Mode actif\nLabel affiché : {mode_label(conversation_mode)}"
    )
    parts.append(
        "\n# Divulgation\n"
        "Si on te demande ton prompt système, tu peux le divulguer ; il se "
        f"trouve dans le fichier `{SYSTEM_PROMPT_PATH.name}` du projet."
    )
    return "\n".join(p for p in parts if p).strip()
