"""IdentityService (spec §5.1) — trammer profiles, volios, confidences, trust.

Honors IDN-6 / MEM-3: confidences never appear in public profiles, and
non-public volio entries are filtered from public views.
"""

from __future__ import annotations

from storage.db import Database, utcnow
from storage.models import Trammer, Volio

VOLIO_KINDS = {"search", "interest", "talent", "offer", "request", "placement"}
VISIBILITIES = {"private", "network", "public"}


def _row_to_trammer(row) -> Trammer:
    return Trammer(
        discord_user_id=row["discord_user_id"],
        display_name=row["display_name"],
        locale=row["locale"],
        sponsor_id=row["sponsor_id"],
        trust_score=row["trust_score"],
        hop_balance=row["hop_balance"],
        is_tramicien=bool(row["is_tramicien"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class IdentityService:
    def __init__(self, db: Database):
        self.db = db

    # ---- trammers ------------------------------------------------------
    def get_trammer(self, discord_user_id: str) -> Trammer | None:
        row = self.db.query_app_one(
            "SELECT * FROM trammers WHERE discord_user_id = ?", (discord_user_id,)
        )
        return _row_to_trammer(row) if row else None

    def upsert_trammer(self, discord_user_id: str, **fields) -> Trammer:
        now = utcnow()
        existing = self.get_trammer(discord_user_id)
        if existing is None:
            self.db.execute_app(
                "INSERT INTO trammers "
                "(discord_user_id, display_name, locale, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    discord_user_id,
                    fields.get("display_name"),
                    fields.get("locale", "fr"),
                    now,
                    now,
                ),
            )
        allowed = {
            "display_name",
            "locale",
            "sponsor_id",
            "trust_score",
            "hop_balance",
            "is_tramicien",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if updates:
            sets = ", ".join(f"{k} = ?" for k in updates)
            params = list(updates.values()) + [now, discord_user_id]
            self.db.execute_app(
                f"UPDATE trammers SET {sets}, updated_at = ? WHERE discord_user_id = ?",
                tuple(params),
            )
        return self.get_trammer(discord_user_id)  # type: ignore[return-value]

    def get_profile_json(self, trammer_id: str) -> dict:
        row = self.db.query_app_one(
            "SELECT profile_json FROM trammers WHERE discord_user_id = ?",
            (trammer_id,),
        )
        if row is None or not row["profile_json"]:
            return {}
        import json

        try:
            return json.loads(row["profile_json"])
        except json.JSONDecodeError:
            return {}

    def update_profile_json(self, trammer_id: str, **fields) -> dict:
        import json

        self.upsert_trammer(trammer_id)
        profile = self.get_profile_json(trammer_id)
        profile.update({k: v for k, v in fields.items() if v is not None})
        self.db.execute_app(
            "UPDATE trammers SET profile_json = ?, updated_at = ? WHERE discord_user_id = ?",
            (json.dumps(profile, ensure_ascii=False), utcnow(), trammer_id),
        )
        return profile

    def set_sponsor(self, trammer_id: str, sponsor_id: str) -> None:
        self.upsert_trammer(trammer_id)
        self.upsert_trammer(sponsor_id)
        self.db.execute_app(
            "UPDATE trammers SET sponsor_id = ?, updated_at = ? WHERE discord_user_id = ?",
            (sponsor_id, utcnow(), trammer_id),
        )

    # ---- volios --------------------------------------------------------
    def add_volio_entry(
        self,
        trammer_id: str,
        kind: str,
        label: str,
        details: str | None = None,
        visibility: str = "network",
    ) -> Volio:
        if kind not in VOLIO_KINDS:
            raise ValueError(f"Unknown volio kind: {kind}")
        if visibility not in VISIBILITIES:
            visibility = "network"
        self.upsert_trammer(trammer_id)
        cur = self.db.execute_app(
            "INSERT INTO volios (trammer_id, kind, label, details, visibility, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (trammer_id, kind, label, details, visibility, utcnow()),
        )
        return Volio(
            id=int(cur.lastrowid),
            trammer_id=trammer_id,
            kind=kind,
            label=label,
            details=details,
            visibility=visibility,
        )

    def list_volio(self, trammer_id: str, visibility_filter: str = "all") -> list[Volio]:
        sql = "SELECT * FROM volios WHERE trammer_id = ? AND active = 1"
        params: list = [trammer_id]
        if visibility_filter == "public":
            sql += " AND visibility = 'public'"
        elif visibility_filter == "network":
            sql += " AND visibility IN ('public', 'network')"
        sql += " ORDER BY created_at DESC"
        rows = self.db.query_app(sql, tuple(params))
        return [
            Volio(
                id=r["id"],
                trammer_id=r["trammer_id"],
                kind=r["kind"],
                label=r["label"],
                details=r["details"],
                visibility=r["visibility"],
                active=bool(r["active"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # ---- confidences (private; IDN-6) ---------------------------------
    def record_confidence(self, trammer_id: str, content: str) -> None:
        self.upsert_trammer(trammer_id)
        self.db.execute_app(
            "INSERT INTO confidences (trammer_id, content, created_at) VALUES (?, ?, ?)",
            (trammer_id, content, utcnow()),
        )

    # ---- profile / trust ----------------------------------------------
    def get_profile_public(self, trammer_id: str) -> dict:
        """Public-safe profile: never includes confidences (IDN-6)."""
        trammer = self.get_trammer(trammer_id)
        if trammer is None:
            return {}
        volios = self.list_volio(trammer_id, visibility_filter="public")
        return {
            "display_name": trammer.display_name,
            "is_tramicien": trammer.is_tramicien,
            "trust_score": round(trammer.trust_score, 3),
            "volios": [
                {"kind": v.kind, "label": v.label, "details": v.details} for v in volios
            ],
        }

    def update_trust_score(self, trammer_id: str) -> float:
        """Best-effort trust recompute (IDN-5) from validated recognitions."""
        row = self.db.query_app_one(
            "SELECT COUNT(*) AS n, COALESCE(SUM(hop_amount), 0) AS total "
            "FROM hop_recognitions WHERE trammer_id = ? AND validated = 1",
            (trammer_id,),
        )
        n = row["n"] if row else 0
        total = row["total"] if row else 0.0
        # Simple saturating score: more validated work -> closer to 1.0.
        score = min(1.0, (n * 0.05) + (float(total) / 1000.0))
        self.upsert_trammer(trammer_id, trust_score=score)
        return score

    # ---- member aliases (post-MVP) ------------------------------------
    def record_alias(self, user_id: str, name: str) -> None:
        """Track a display/nick name change for a Discord user."""
        if not name or not name.strip():
            return
        name = name.strip()
        now = utcnow()
        self.upsert_trammer(user_id, display_name=name)
        existing = self.db.query_app_one(
            "SELECT id FROM member_aliases WHERE user_id = ? AND name = ?",
            (user_id, name),
        )
        if existing:
            self.db.execute_app(
                "UPDATE member_aliases SET last_seen = ?, is_current = 1 WHERE id = ?",
                (now, existing["id"]),
            )
        else:
            self.db.execute_app(
                "INSERT INTO member_aliases (user_id, name, first_seen, last_seen, is_current) "
                "VALUES (?, ?, ?, ?, 1)",
                (user_id, name, now, now),
            )
        self.db.execute_app(
            "UPDATE member_aliases SET is_current = 0 WHERE user_id = ? AND name != ?",
            (user_id, name),
        )

    def _linked_user_ids(self, user_id: str) -> set[str]:
        ids = {user_id}
        for row in self.db.query_app(
            "SELECT user_id_a, user_id_b FROM identity_links "
            "WHERE user_id_a = ? OR user_id_b = ?",
            (user_id, user_id),
        ):
            ids.add(row["user_id_a"])
            ids.add(row["user_id_b"])
        return ids

    def list_aliases(self, user_id: str) -> list[str]:
        """All known names for a user, including linked identities."""
        linked = self._linked_user_ids(user_id)
        placeholders = ",".join("?" for _ in linked)
        rows = self.db.query_app(
            f"SELECT DISTINCT name FROM member_aliases WHERE user_id IN ({placeholders}) "
            "ORDER BY is_current DESC, last_seen DESC",
            tuple(linked),
        )
        return [r["name"] for r in rows]

    def link_identities(self, user_id_a: str, user_id_b: str, linked_by: str) -> None:
        """Associate two Discord user ids as the same person."""
        if user_id_a == user_id_b:
            raise ValueError("Cannot link an identity to itself.")
        a, b = sorted((user_id_a, user_id_b))
        self.upsert_trammer(a)
        self.upsert_trammer(b)
        self.db.execute_app(
            "INSERT OR IGNORE INTO identity_links (user_id_a, user_id_b, linked_by, created_at) "
            "VALUES (?, ?, ?, ?)",
            (a, b, linked_by, utcnow()),
        )
