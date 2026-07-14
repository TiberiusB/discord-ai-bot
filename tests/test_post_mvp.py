"""Tests for post-MVP features: traces, identity, governance, capabilities."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bot.capabilities import build_capabilities_note, can, save_capabilities_snapshot
from bot.config import Settings, PROJECT_ROOT
from services.governance import SignalementSpec
from services.identity import IdentityService
from services.memory import MemoryService
from storage.db import build_database
from storage.history import HistoryStore
from storage.models import DiscordMessageSnapshot


@pytest.fixture
def db_settings(tmp_path: Path) -> Settings:
    raw = {
        "bot": {"prefix": "!ai", "locale_default": "fr", "timezone": "America/Montreal"},
        "channels": {"log_mode": "allowlist", "allowlist": ["111"], "denylist": []},
        "governance": {"escalation_threshold": 2},
        "social_norms_defaults": {
            "dm_always_private": True,
            "confidences_never_shared": True,
        },
    }
    return Settings(
        raw=raw,
        discord_token="test",
        data_dir=tmp_path / "data",
        project_root=PROJECT_ROOT,
        docs_dir=PROJECT_ROOT / "docs",
        prompts_dir=PROJECT_ROOT / "prompts",
    )


@pytest.fixture
def db_bundle(db_settings: Settings):
    db = build_database(db_settings)
    history = HistoryStore(db)
    yield db_settings, db, history
    db.close()


def _log_messages(history: HistoryStore, user_id: str, name: str, n: int = 3) -> None:
    for i in range(n):
        history.log_message(
            DiscordMessageSnapshot(
                guild_id="g1",
                channel_id="111",
                user_id=user_id,
                user_name=name,
                is_dm=False,
                content=f"msg {i}",
                created_at=f"2026-07-1{i}T10:00:00+00:00",
            )
        )


def test_forget_user_records_activity_trace(db_bundle):
    settings, db, history = db_bundle
    memory = MemoryService(db, history, settings)
    uid = "user-42"
    _log_messages(history, uid, "Alice", 4)

    result = memory.forget_user(uid)
    assert result.messages_deleted == 4
    assert result.trace_recorded is True

    row = db.query_app_one("SELECT * FROM activity_traces WHERE user_id = ?", (uid,))
    assert row is not None
    assert row["display_name"] == "Alice"
    assert row["message_count"] == 4
    assert row["first_activity"] == "2026-07-10T10:00:00+00:00"
    assert row["last_activity"] == "2026-07-13T10:00:00+00:00"


def test_identity_aliases_and_links(db_bundle):
    _, db, _ = db_bundle
    identity = IdentityService(db)

    identity.record_alias("u1", "Alice")
    identity.record_alias("u1", "Alicia")
    names = identity.list_aliases("u1")
    assert "Alice" in names
    assert "Alicia" in names

    identity.record_alias("u2", "Bob")
    identity.link_identities("u1", "u2", "admin-1")
    merged = identity.list_aliases("u2")
    assert "Alice" in merged or "Alicia" in merged
    assert "Bob" in merged


def test_governance_evaluate_moderation_threshold(db_bundle):
    settings, db, history = db_bundle
    from services.governance import GovernanceService

    governance = GovernanceService(db, history, settings=settings)
    governance.file_signalement("r1", SignalementSpec("target-1", 2, "first"))
    assert governance.evaluate_moderation("target-1") is None

    governance.file_signalement("r2", SignalementSpec("target-1", 2, "second"))
    suggestion = governance.evaluate_moderation("target-1")
    assert suggestion is not None
    assert suggestion.open_count == 2
    assert "suspendre" in suggestion.action


def test_governance_level3_triggers_immediate_suggestion(db_bundle):
    settings, db, history = db_bundle
    from services.governance import GovernanceService

    governance = GovernanceService(db, history, settings=settings)
    governance.file_signalement("r1", SignalementSpec("target-9", 3, "danger"))
    suggestion = governance.evaluate_moderation("target-9")
    assert suggestion is not None
    assert suggestion.level3_count == 1
    assert "bannir" in suggestion.action


def test_capabilities_note_and_can(db_settings: Settings):
    snapshot = {
        "scanned_at": "2026-07-14T12:00:00+00:00",
        "guild_id": "999",
        "guild_permissions": {
            "send_messages": True,
            "send_tts_messages": True,
            "create_public_threads": False,
            "manage_events": True,
        },
        "channels": {
            "111": {
                "send_messages": True,
                "create_public_threads": True,
                "send_tts_messages": False,
            }
        },
        "strategy": {"threads": "oui", "tts": "oui (/say)"},
    }
    save_capabilities_snapshot(db_settings, snapshot)
    note = build_capabilities_note(snapshot)
    assert "Capacités Discord" in note
    assert can(snapshot, "send_tts_messages") is True
    assert can(snapshot, "send_tts_messages", "111") is False
    assert can(snapshot, "create_public_threads", "111") is True
