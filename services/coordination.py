"""CoordinationService (spec §5.3) — events, RSVPs, teams.

Events are *proposed* (CRD-1, NFR-1): creation yields a ``proposed`` record; a
human confirms via the Discord confirmation UI before it becomes ``confirmed``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from storage.db import Database, utcnow
from storage.models import Event, Team


@dataclass
class EventSpec:
    title: str
    starts_at: str | None = None
    duration_min: int | None = None
    location: str | None = None
    min_attendees: int = 1
    max_attendees: int | None = None
    metadata: dict | None = None


def _row_to_event(row) -> Event:
    return Event(
        id=row["id"],
        organizer_id=row["organizer_id"],
        title=row["title"],
        starts_at=row["starts_at"],
        duration_min=row["duration_min"],
        location=row["location"],
        min_attendees=row["min_attendees"],
        max_attendees=row["max_attendees"],
        status=row["status"],
        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        created_at=row["created_at"],
    )


class CoordinationService:
    def __init__(self, db: Database):
        self.db = db

    def propose_event(self, organizer_id: str, spec: EventSpec) -> Event:
        event_id = str(uuid.uuid4())
        self.db.execute_app(
            "INSERT INTO events (id, organizer_id, title, starts_at, duration_min, "
            "location, min_attendees, max_attendees, status, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?, ?)",
            (
                event_id,
                organizer_id,
                spec.title,
                spec.starts_at,
                spec.duration_min,
                spec.location,
                spec.min_attendees,
                spec.max_attendees,
                json.dumps(spec.metadata or {}),
                utcnow(),
            ),
        )
        return self.get_event(event_id)  # type: ignore[return-value]

    def confirm_event(self, event_id: str) -> None:
        self.db.execute_app(
            "UPDATE events SET status = 'confirmed' WHERE id = ?", (event_id,)
        )

    def cancel_event(self, event_id: str) -> None:
        self.db.execute_app(
            "UPDATE events SET status = 'cancelled' WHERE id = ?", (event_id,)
        )

    def get_event(self, event_id: str) -> Event | None:
        row = self.db.query_app_one("SELECT * FROM events WHERE id = ?", (event_id,))
        return _row_to_event(row) if row else None

    def rsvp(self, event_id: str, trammer_id: str, status: str) -> None:
        self.db.execute_app(
            "INSERT INTO event_rsvps (event_id, trammer_id, status) VALUES (?, ?, ?) "
            "ON CONFLICT(event_id, trammer_id) DO UPDATE SET status = excluded.status",
            (event_id, trammer_id, status),
        )

    def list_upcoming_events(self, trammer_id: str | None = None) -> list[Event]:
        rows = self.db.query_app(
            "SELECT * FROM events WHERE status IN ('proposed', 'confirmed') "
            "ORDER BY COALESCE(starts_at, created_at) ASC LIMIT 25"
        )
        return [_row_to_event(r) for r in rows]

    def create_team(self, member_ids: list[str], name: str | None = None) -> Team:
        team_id = str(uuid.uuid4())
        now = utcnow()
        self.db.execute_app(
            "INSERT INTO teams (id, name, created_at) VALUES (?, ?, ?)",
            (team_id, name, now),
        )
        for member_id in member_ids:
            self.db.execute_app(
                "INSERT OR IGNORE INTO team_members (team_id, trammer_id, joined_at) "
                "VALUES (?, ?, ?)",
                (team_id, member_id, now),
            )
        return Team(id=team_id, name=name, member_ids=list(member_ids), created_at=now)
