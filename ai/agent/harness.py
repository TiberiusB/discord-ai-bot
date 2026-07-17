"""Dual harness: procedural vs creative conversation paths."""

from __future__ import annotations

CONVERSATION_MODES: dict[str, str] = {
    "listen": "Je vous écoute.",
    "question": "Je vous questionne.",
    "cosmos": "Voici les nouvelles du cosmos.",
    "wishes": "Concernant vos souhaits et options.",
    "chat": "Tchitt-tchatt.",
    "solve": "Résolvons un problème.",
}

PROCEDURAL_MODES = frozenset({"cosmos", "wishes", "solve"})
CREATIVE_MODES = frozenset({"listen", "question", "chat"})

DEFAULT_MODE = "listen"


def normalize_mode(mode: str | None) -> str:
    if not mode:
        return DEFAULT_MODE
    key = mode.strip().lower()
    if key in CONVERSATION_MODES:
        return key
    for k, label in CONVERSATION_MODES.items():
        if key == label.lower():
            return k
    return DEFAULT_MODE


def harness_for_mode(mode: str | None) -> str:
    key = normalize_mode(mode)
    return "procedural" if key in PROCEDURAL_MODES else "creative"


def mode_label(mode: str | None) -> str:
    return CONVERSATION_MODES.get(normalize_mode(mode), CONVERSATION_MODES[DEFAULT_MODE])
