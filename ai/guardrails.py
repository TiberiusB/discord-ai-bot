"""Input/output guardrails (spec §3.3 post-checks, §10.3).

- ``sanitize_input``: strip ``@everyone`` / ``@here`` from user text before it
  reaches the agent (prevents prompt-driven mass pings).
- ``postprocess_output``: enforce feminine self-reference in French, and remove
  links whose host is not on the allowlist (strip fabricated URLs).
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

_MASS_MENTION = re.compile(r"@(everyone|here)", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s)>\]]+")

# Common masculine -> feminine self-references (best-effort; French Québec voice).
# Group 1 preserves the original "je suis " / "je serais " casing.
_FEMININE_FIXES = [
    (re.compile(r"\b(je suis )actif\b", re.IGNORECASE), r"\1active"),
    (re.compile(r"\b(je suis )désolé\b", re.IGNORECASE), r"\1désolée"),
    (re.compile(r"\b(je suis )ravi\b", re.IGNORECASE), r"\1ravie"),
    (re.compile(r"\b(je suis )prêt\b", re.IGNORECASE), r"\1prête"),
    (re.compile(r"\b(je suis )heureux\b", re.IGNORECASE), r"\1heureuse"),
    (re.compile(r"\b(je suis )content\b", re.IGNORECASE), r"\1contente"),
    (re.compile(r"\b(je suis )certain\b", re.IGNORECASE), r"\1certaine"),
    (re.compile(r"\b(je suis )sûr\b", re.IGNORECASE), r"\1sûre"),
    (re.compile(r"\b(je serais )heureux\b", re.IGNORECASE), r"\1heureuse"),
]

_DEFAULT_ALLOWED_HOSTS = {
    "latramice.net",
    "la-tramice.net",
    "cdn.discordapp.com",
    "media.discordapp.net",
    "discord.com",
}


def sanitize_input(text: str) -> str:
    if not text:
        return text
    return _MASS_MENTION.sub(lambda m: m.group(0).replace("@", ""), text)


def _allowed_hosts(settings) -> set[str]:
    hosts = set(_DEFAULT_ALLOWED_HOSTS)
    for host in settings.get("fetch_allowlist", []) or []:
        hosts.add(str(host).lower())
    return hosts


def _apply_feminine(text: str) -> str:
    for pattern, replacement in _FEMININE_FIXES:
        text = pattern.sub(replacement, text)
    return text


def _strip_disallowed_links(text: str, allowed: set[str]) -> str:
    def _check(match: re.Match) -> str:
        url = match.group(0)
        host = (urlparse(url).hostname or "").lower()
        host = host[4:] if host.startswith("www.") else host
        if host in allowed or any(host.endswith("." + a) for a in allowed):
            return url
        return "[lien retiré]"

    return _URL_RE.sub(_check, text)


def postprocess_output(text: str, settings, locale: str = "fr") -> str:
    """Apply feminine self-reference + link allowlist to a model response."""
    if not text:
        return text
    if locale == "fr":
        text = _apply_feminine(text)
    text = _strip_disallowed_links(text, _allowed_hosts(settings))
    return text
