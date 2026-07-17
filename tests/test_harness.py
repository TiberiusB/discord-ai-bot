"""Tests for conversation mode → harness mapping."""

from ai.agent.harness import harness_for_mode, normalize_mode


def test_default_mode_is_listen():
    assert normalize_mode(None) == "listen"
    assert harness_for_mode(None) == "creative"


def test_procedural_modes():
    for key in ("cosmos", "wishes", "solve"):
        assert harness_for_mode(key) == "procedural"


def test_creative_modes():
    for key in ("listen", "question", "chat"):
        assert harness_for_mode(key) == "creative"
