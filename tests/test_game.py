"""Tests for game placement window and reallocation."""

import pytest

from bot.config import Settings
from services.game import GameError, GameService
from storage.db import build_database


@pytest.fixture
def game_db(tmp_path):
    settings = Settings(
        raw={"bot": {"timezone": "America/Montreal"}},
        data_dir=tmp_path / "data",
    )
    db = build_database(settings)
    yield db, settings
    db.close()


def test_place_rejects_when_not_investing(game_db):
    db, settings = game_db
    game = GameService(db, settings)
    week = game.get_current_week()
    db.execute_app(
        "INSERT INTO trammers (discord_user_id, created_at, updated_at) "
        "VALUES ('u1', '2026-01-01', '2026-01-01'), ('u2', '2026-01-01', '2026-01-01')"
    )
    db.execute_app(
        "INSERT INTO entities (id, kind, owner_id, title, created_at, updated_at) "
        "VALUES ('e1', 'mission', 'u2', 'Mission test', '2026-01-01', '2026-01-01')"
    )
    game.set_week_status(week.week_id, "closed")
    with pytest.raises(GameError, match="fenêtre"):
        game.place_hops("u1", "e1", 5.0)


def test_self_placement_blocked(game_db):
    db, settings = game_db
    game = GameService(db, settings)
    week = game.get_current_week()
    game.set_week_status(week.week_id, "investing")
    db.execute_app(
        "INSERT INTO trammers (discord_user_id, created_at, updated_at) "
        "VALUES ('u1', '2026-01-01', '2026-01-01')"
    )
    db.execute_app(
        "INSERT INTO entities (id, kind, owner_id, title, created_at, updated_at) "
        "VALUES ('e1', 'mission', 'u1', 'Ma mission', '2026-01-01', '2026-01-01')"
    )
    with pytest.raises(GameError, match="propre"):
        game.place_hops("u1", "e1", 1.0)


def test_place_hops_returns_total_on_entity(game_db):
    db, settings = game_db
    game = GameService(db, settings)
    week = game.get_current_week()
    game.set_week_status(week.week_id, "investing")
    db.execute_app(
        "INSERT INTO trammers (discord_user_id, created_at, updated_at) "
        "VALUES ('u1', '2026-01-01', '2026-01-01'), ('u2', '2026-01-01', '2026-01-01')"
    )
    db.execute_app(
        "INSERT INTO entities (id, kind, owner_id, title, created_at, updated_at) "
        "VALUES ('e1', 'mission', 'u2', 'Mission test', '2026-01-01', '2026-01-01')"
    )
    first = game.place_hops("u1", "e1", 3.0)
    assert first.hop_amount == 3.0
    second = game.place_hops("u1", "e1", 2.0)
    assert second.hop_amount == 5.0
