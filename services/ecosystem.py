"""EcosystemService (spec §5.5) — the Mondo map and entity dashboards.

Perso view filters by the trammer's volio affinities; Cosmo view is unfiltered
and ranks globally by urgency, transparency, then HOP requested (ECO-2, ECO-5).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from storage.db import Database, utcnow
from storage.models import Entity


@dataclass
class MondoFilters:
    kind: str | None = None
    phase: str | None = None
    query: str | None = None
    limit: int = 15


def _row_to_entity(row) -> Entity:
    return Entity(
        id=row["id"],
        kind=row["kind"],
        owner_id=row["owner_id"],
        title=row["title"],
        description=row["description"],
        phase=row["phase"],
        transparency=row["transparency"],
        hop_requested=row["hop_requested"],
        hop_allocated=row["hop_allocated"],
        location=row["location"],
        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class EcosystemService:
    def __init__(self, db: Database):
        self.db = db

    def create_entity(
        self,
        kind: str,
        owner_id: str,
        title: str,
        description: str | None = None,
        hop_requested: float = 0.0,
        location: str | None = None,
        metadata: dict | None = None,
    ) -> Entity:
        entity_id = str(uuid.uuid4())
        now = utcnow()
        self.db.execute_app(
            "INSERT INTO entities (id, kind, owner_id, title, description, phase, "
            "transparency, hop_requested, hop_allocated, location, metadata, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'draft', 0.5, ?, 0.0, ?, ?, ?, ?)",
            (
                entity_id,
                kind,
                owner_id,
                title,
                description,
                hop_requested,
                location,
                json.dumps(metadata or {}),
                now,
                now,
            ),
        )
        return self.get_entity(entity_id)  # type: ignore[return-value]

    def get_entity(self, entity_id: str) -> Entity | None:
        row = self.db.query_app_one("SELECT * FROM entities WHERE id = ?", (entity_id,))
        return _row_to_entity(row) if row else None

    def get_entity_dashboard(self, entity_id: str, week_id: str | None = None) -> dict:
        entity = self.get_entity(entity_id)
        if entity is None:
            return {}
        updates = self.db.query_app(
            "SELECT * FROM entity_updates WHERE entity_id = ? ORDER BY created_at DESC LIMIT 20",
            (entity_id,),
        )
        support = self.db.query_app_one(
            "SELECT COUNT(DISTINCT trammer_id) AS backers, COALESCE(SUM(hop_amount),0) AS hops "
            "FROM hop_placements WHERE entity_id = ?",
            (entity_id,),
        )
        week_filter = ""
        params: list = [entity_id]
        if week_id:
            week_filter = " AND week_id = ?"
            params.append(week_id)
        placements = self.db.query_app(
            "SELECT p.*, e.title AS entity_title FROM hop_placements p "
            "JOIN entities e ON e.id = p.entity_id "
            f"WHERE p.entity_id = ?{week_filter} ORDER BY placed_at DESC",
            tuple(params),
        )
        recognitions = self.db.query_app(
            "SELECT * FROM hop_recognitions WHERE entity_id = ? ORDER BY created_at DESC LIMIT 10",
            (entity_id,),
        )
        return {
            "entity": entity,
            "backers": support["backers"] if support else 0,
            "hops_placed": support["hops"] if support else 0.0,
            "updates": [dict(u) for u in updates],
            "placements": [dict(p) for p in placements],
            "recognitions": [dict(r) for r in recognitions],
        }

    def add_entity_update(self, entity_id: str, author_id: str, body: str) -> dict:
        if not body.strip():
            raise ValueError("Commentaire vide.")
        if self.get_entity(entity_id) is None:
            raise ValueError("Entité introuvable.")
        now = utcnow()
        cur = self.db.execute_app(
            "INSERT INTO entity_updates (entity_id, author_id, body, created_at) "
            "VALUES (?, ?, ?, ?)",
            (entity_id, author_id, body.strip(), now),
        )
        self.db.execute_app(
            "UPDATE entities SET updated_at = ? WHERE id = ?",
            (now, entity_id),
        )
        row = self.db.query_app_one(
            "SELECT * FROM entity_updates WHERE id = ?", (cur.lastrowid,)
        )
        return dict(row) if row else {}

    def list_mondo(
        self, view: str, trammer_id: str | None, filters: MondoFilters
    ) -> list[Entity]:
        sql = "SELECT * FROM entities WHERE phase != 'archived'"
        params: list = []
        if filters.kind:
            sql += " AND kind = ?"
            params.append(filters.kind)
        if filters.phase:
            sql += " AND phase = ?"
            params.append(filters.phase)
        if filters.query:
            sql += " AND (title LIKE ? OR description LIKE ?)"
            like = f"%{filters.query}%"
            params.extend([like, like])

        if view == "cosmo":
            # Global urgency proxy: unmet HOP need, then transparency (ECO-2/ECO-5).
            sql += (
                " ORDER BY (hop_requested - hop_allocated) DESC, "
                "transparency DESC, hop_requested DESC"
            )
        else:  # perso: transparency-first, most recent activity
            sql += " ORDER BY transparency DESC, updated_at DESC"
        sql += " LIMIT ?"
        params.append(filters.limit)

        rows = self.db.query_app(sql, tuple(params))
        entities = [_row_to_entity(r) for r in rows]

        if view == "perso" and trammer_id:
            entities = self._filter_perso(trammer_id, entities)
        return entities

    def _filter_perso(self, trammer_id: str, entities: list[Entity]) -> list[Entity]:
        """Rank by overlap with the trammer's volio labels (affinity)."""
        volio_rows = self.db.query_app(
            "SELECT label FROM volios WHERE trammer_id = ? AND active = 1", (trammer_id,)
        )
        terms = {r["label"].lower() for r in volio_rows}
        if not terms:
            return entities

        def affinity(e: Entity) -> int:
            blob = f"{e.title} {e.description or ''}".lower()
            return sum(1 for t in terms if t and t in blob)

        return sorted(entities, key=affinity, reverse=True)

    def get_playtest_stats(self) -> dict:
        counts = self.db.query_app(
            "SELECT kind, COUNT(*) AS n FROM entities GROUP BY kind"
        )
        totals = self.db.query_app_one(
            "SELECT COUNT(*) AS trammers FROM trammers"
        )
        return {
            "entities_by_kind": {r["kind"]: r["n"] for r in counts},
            "trammers": totals["trammers"] if totals else 0,
        }

    def get_social_stats(self) -> dict:
        """Aggregate salon vs DM activity from the message log."""
        salon_users = self.db.query_history_one(
            "SELECT COUNT(DISTINCT user_id) AS n FROM messages "
            "WHERE deleted = 0 AND is_dm = 0"
        )
        dm_users = self.db.query_history_one(
            "SELECT COUNT(DISTINCT user_id) AS n FROM messages "
            "WHERE deleted = 0 AND is_dm = 1"
        )
        salon_msgs = self.db.query_history_one(
            "SELECT COUNT(*) AS n FROM messages WHERE deleted = 0 AND is_dm = 0"
        )
        dm_msgs = self.db.query_history_one(
            "SELECT COUNT(*) AS n FROM messages WHERE deleted = 0 AND is_dm = 1"
        )
        bot_prefix = self.db.query_history_one(
            "SELECT COUNT(*) AS n FROM messages WHERE deleted = 0 AND "
            "(content LIKE '!ai%' OR content LIKE '%<@%')"
        )
        return {
            "distinct_salon_users": salon_users["n"] if salon_users else 0,
            "distinct_dm_users": dm_users["n"] if dm_users else 0,
            "salon_messages": salon_msgs["n"] if salon_msgs else 0,
            "dm_messages": dm_msgs["n"] if dm_msgs else 0,
            "bot_addressed_estimate": bot_prefix["n"] if bot_prefix else 0,
        }
