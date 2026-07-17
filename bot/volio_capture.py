"""Heuristic capture of wishes/offers from messages addressed to the bot."""

from __future__ import annotations

import re

_WISH = re.compile(
    r"\b(je cherche|j'aimerais|je voudrais|j'aurais besoin|besoin de)\b",
    re.IGNORECASE,
)
_OFFER = re.compile(
    r"\b(je propose|j'offre|je peux aider|je suis disponible pour)\b",
    re.IGNORECASE,
)


def capture_volio_from_message(content: str) -> tuple[str, str] | None:
    """Return (kind, label) if message looks like a wish or offer."""
    text = (content or "").strip()
    if len(text) < 12:
        return None
    if _OFFER.search(text):
        return "offer", text[:120]
    if _WISH.search(text):
        return "search", text[:120]
    return None
