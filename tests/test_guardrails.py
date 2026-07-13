"""Tests for input guardrails."""

from ai.guardrails import sanitize_input
from bot.config import Settings


def test_sanitize_strips_everyone() -> None:
    assert "@everyone" not in sanitize_input("hello @everyone world")


def test_postprocess_strips_unknown_links() -> None:
    from ai.guardrails import postprocess_output

    s = Settings(raw={"fetch_allowlist": ["latramice.net"]})
    out = postprocess_output(
        "Voir https://evil.example.com/page", s, locale="fr"
    )
    assert "evil.example.com" not in out
    assert "[lien retiré]" in out
