"""GameService (spec §5.4) — weekly cycle + HOP workflow (simulation).

Enforces the HOP rules from spec §4.2 / requirements §5.2-§5.3:
- amounts rounded to hundredths (2 decimals),
- no negative balances; individual carnet cap 99 999,99 HOPs,
- max 100 HOPs invested per person per week,
- placements only in entities other than one's own.

This is a best-effort playtest simulation, not a financial ledger.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from storage.db import Database, utcnow
from storage.models import Entity, GameWeek, Placement

HOP_MIN = 0.0
HOP_MAX_BALANCE = 99_999.99
HOP_DECIMALS = 2
HOP_MAX_INVEST_PER_WEEK = 100.0


class GameError(ValueError):
    """Raised when a HOP rule is violated (surfaced to the user in French)."""


def round_hop(amount: float) -> float:
    return round(float(amount), HOP_DECIMALS)


@dataclass
class MissionSpec:
    title: str
    description: str | None = None
    hop_requested: float = 0.0
    location: str | None = None


def _row_to_week(row) -> GameWeek:
    return GameWeek(
        week_id=row["week_id"],
        starts_at=row["starts_at"],
        invest_end=row["invest_end"],
        hop_created=row["hop_created"],
        growth_factor=row["growth_factor"],
        influence_min=row["influence_min"],
        influence_max=row["influence_max"],
        aum_per_trammer=row["aum_per_trammer"],
        status=row["status"],
    )


class GameService:
    def __init__(self, db: Database, settings):
        self.db = db
        self.settings = settings
        self.tz = ZoneInfo(settings.timezone)

    # ---- weekly cycle --------------------------------------------------
    def _week_bounds(self, now: datetime) -> tuple[str, str, str]:
        """Return (week_id, starts_at Thu 17:00, invest_end Sun 23:59:59) local."""
        # Anchor on the Thursday of the ISO week containing ``now``.
        monday = now - timedelta(days=now.weekday())
        thursday = monday + timedelta(days=3)
        starts = thursday.replace(hour=17, minute=0, second=0, microsecond=0)
        invest_end = (starts + timedelta(days=3)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        iso = starts.isocalendar()
        week_id = f"{iso.year}-W{iso.week:02d}"
        return week_id, starts.isoformat(), invest_end.isoformat()

    def get_current_week(self) -> GameWeek:
        now = datetime.now(self.tz)
        week_id, starts_at, invest_end = self._week_bounds(now)
        row = self.db.query_app_one(
            "SELECT * FROM game_weeks WHERE week_id = ?", (week_id,)
        )
        if row is None:
            self.db.execute_app(
                "INSERT INTO game_weeks (week_id, starts_at, invest_end, status) "
                "VALUES (?, ?, ?, 'open')",
                (week_id, starts_at, invest_end),
            )
            row = self.db.query_app_one(
                "SELECT * FROM game_weeks WHERE week_id = ?", (week_id,)
            )
        return _row_to_week(row)

    def set_week_status(self, week_id: str, status: str) -> None:
        self.db.execute_app(
            "UPDATE game_weeks SET status = ? WHERE week_id = ?", (status, week_id)
        )

    def compute_influence_budget(self, week_id: str | None = None) -> float:
        """Per-trammer influence budget = avg HOPs created last week +20%, clamp [5,100]."""
        week = self.get_current_week() if week_id is None else self._get_week(week_id)
        # Previous week's created HOPs.
        prev = self.db.query_app_one(
            "SELECT hop_created FROM game_weeks WHERE week_id < ? ORDER BY week_id DESC LIMIT 1",
            (week.week_id,),
        )
        prev_created = prev["hop_created"] if prev else 0.0
        trammers = self.db.query_app_one("SELECT COUNT(*) AS n FROM trammers")["n"] or 1
        avg = prev_created / trammers
        budget = avg * week.growth_factor
        budget = max(week.influence_min, min(week.influence_max, budget))
        return round_hop(budget)

    def _get_week(self, week_id: str) -> GameWeek:
        row = self.db.query_app_one("SELECT * FROM game_weeks WHERE week_id = ?", (week_id,))
        if row is None:
            raise GameError(f"Semaine inconnue : {week_id}")
        return _row_to_week(row)

    def _ensure_invest_window(self, week: GameWeek) -> None:
        """Reject placements outside Thu 17:00 – Sun 23:59:59 when not investing."""
        if week.status not in {"investing", "open"}:
            raise GameError(
                "La fenêtre de placement est fermée pour cette semaine. "
                "Attends l'ouverture (jeudi 17 h) ou consulte les annonces."
            )
        now = datetime.now(self.tz)
        starts = datetime.fromisoformat(week.starts_at)
        if starts.tzinfo is None:
            starts = starts.replace(tzinfo=self.tz)
        end = datetime.fromisoformat(week.invest_end)
        if end.tzinfo is None:
            end = end.replace(tzinfo=self.tz)
        if now < starts or now > end:
            raise GameError(
                "Les placements ne sont possibles que du jeudi 17 h au dimanche minuit "
                f"(semaine {week.week_id})."
            )

    def update_week_params(self, week_id: str, **fields) -> GameWeek:
        allowed = {
            "starts_at",
            "invest_end",
            "growth_factor",
            "influence_min",
            "influence_max",
            "aum_per_trammer",
            "status",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self._get_week(week_id)
        sets = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [week_id]
        self.db.execute_app(
            f"UPDATE game_weeks SET {sets} WHERE week_id = ?",
            tuple(params),
        )
        return self._get_week(week_id)

    # ---- missions / quests --------------------------------------------
    def publish_mission(self, owner_id: str, spec: MissionSpec) -> Entity:
        return self._publish_entity("mission", owner_id, spec)

    def publish_quest(self, owner_id: str, spec: MissionSpec) -> Entity:
        return self._publish_entity("quest", owner_id, spec)

    def _publish_entity(self, kind: str, owner_id: str, spec: MissionSpec) -> Entity:
        import uuid

        entity_id = str(uuid.uuid4())
        now = utcnow()
        self.db.execute_app(
            "INSERT INTO entities (id, kind, owner_id, title, description, phase, "
            "transparency, hop_requested, hop_allocated, location, metadata, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'active', 0.5, ?, 0.0, ?, ?, ?, ?)",
            (
                entity_id,
                kind,
                owner_id,
                spec.title,
                spec.description,
                round_hop(spec.hop_requested),
                spec.location,
                json.dumps({}),
                now,
                now,
            ),
        )
        row = self.db.query_app_one("SELECT * FROM entities WHERE id = ?", (entity_id,))
        if row is None:
            raise GameError(f"Impossible de créer l'entité : {entity_id}")
        from services.ecosystem import _row_to_entity

        return _row_to_entity(row)

    # ---- placements (investment) --------------------------------------
    def placed_this_week(self, trammer_id: str, week_id: str) -> float:
        row = self.db.query_app_one(
            "SELECT COALESCE(SUM(hop_amount), 0) AS total FROM hop_placements "
            "WHERE week_id = ? AND trammer_id = ?",
            (week_id, trammer_id),
        )
        return round_hop(row["total"] if row else 0.0)

    def list_placements(self, trammer_id: str, week_id: str | None = None) -> list[Placement]:
        week = self.get_current_week() if week_id is None else self._get_week(week_id)
        rows = self.db.query_app(
            "SELECT week_id, trammer_id, entity_id, hop_amount, placed_at "
            "FROM hop_placements WHERE week_id = ? AND trammer_id = ?",
            (week.week_id, trammer_id),
        )
        return [
            Placement(
                week_id=r["week_id"],
                trammer_id=r["trammer_id"],
                entity_id=r["entity_id"],
                hop_amount=r["hop_amount"],
                placed_at=r["placed_at"],
            )
            for r in rows
        ]

    def _validate_entity_for_placement(self, trammer_id: str, entity_id: str):
        entity = self.db.query_app_one(
            "SELECT owner_id, title FROM entities WHERE id = ?", (entity_id,)
        )
        if entity is None:
            raise GameError("Entité introuvable.")
        if entity["owner_id"] == trammer_id:
            raise GameError(
                "On ne place pas d'influence dans sa propre mission, entreprise ou entité."
            )
        return entity

    def _check_weekly_cap(self, trammer_id: str, week_id: str, new_total: float) -> None:
        if new_total > HOP_MAX_INVEST_PER_WEEK:
            already = self.placed_this_week(trammer_id, week_id)
            raise GameError(
                f"Plafond hebdomadaire dépassé : {already:.2f} → {new_total:.2f} > "
                f"{HOP_MAX_INVEST_PER_WEEK:.0f} HOP."
            )

    def set_placement(self, trammer_id: str, entity_id: str, amount: float) -> Placement | None:
        """Set absolute HOP amount on an entity (0 removes the placement)."""
        amount = round_hop(amount)
        week = self.get_current_week()
        self._ensure_invest_window(week)
        self._validate_entity_for_placement(trammer_id, entity_id)
        existing = self.db.query_app_one(
            "SELECT hop_amount FROM hop_placements WHERE week_id = ? AND trammer_id = ? "
            "AND entity_id = ?",
            (week.week_id, trammer_id, entity_id),
        )
        prev = round_hop(existing["hop_amount"]) if existing else 0.0
        total = self.placed_this_week(trammer_id, week.week_id) - prev + amount
        self._check_weekly_cap(trammer_id, week.week_id, total)
        if amount <= HOP_MIN:
            self.db.execute_app(
                "DELETE FROM hop_placements WHERE week_id = ? AND trammer_id = ? "
                "AND entity_id = ?",
                (week.week_id, trammer_id, entity_id),
            )
            return None
        self.db.execute_app(
            "INSERT INTO hop_placements (week_id, trammer_id, entity_id, hop_amount, placed_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(week_id, trammer_id, entity_id) "
            "DO UPDATE SET hop_amount = excluded.hop_amount, placed_at = excluded.placed_at",
            (week.week_id, trammer_id, entity_id, amount, utcnow()),
        )
        return Placement(
            week_id=week.week_id,
            trammer_id=trammer_id,
            entity_id=entity_id,
            hop_amount=amount,
        )

    def move_hops(
        self, trammer_id: str, from_entity_id: str, to_entity_id: str, amount: float
    ) -> Placement:
        amount = round_hop(amount)
        if amount <= HOP_MIN:
            raise GameError("Le montant doit être positif (2 décimales).")
        if from_entity_id == to_entity_id:
            raise GameError("Source et destination identiques.")
        week = self.get_current_week()
        self._ensure_invest_window(week)
        src = self.db.query_app_one(
            "SELECT hop_amount FROM hop_placements WHERE week_id = ? AND trammer_id = ? "
            "AND entity_id = ?",
            (week.week_id, trammer_id, from_entity_id),
        )
        if src is None or round_hop(src["hop_amount"]) < amount:
            raise GameError("Montant insuffisant sur la source.")
        self._validate_entity_for_placement(trammer_id, to_entity_id)
        new_src = round_hop(src["hop_amount"] - amount)
        if new_src <= HOP_MIN:
            self.db.execute_app(
                "DELETE FROM hop_placements WHERE week_id = ? AND trammer_id = ? "
                "AND entity_id = ?",
                (week.week_id, trammer_id, from_entity_id),
            )
        else:
            self.db.execute_app(
                "UPDATE hop_placements SET hop_amount = ?, placed_at = ? "
                "WHERE week_id = ? AND trammer_id = ? AND entity_id = ?",
                (new_src, utcnow(), week.week_id, trammer_id, from_entity_id),
            )
        dest = self.db.query_app_one(
            "SELECT hop_amount FROM hop_placements WHERE week_id = ? AND trammer_id = ? "
            "AND entity_id = ?",
            (week.week_id, trammer_id, to_entity_id),
        )
        new_dest = round_hop((dest["hop_amount"] if dest else 0.0) + amount)
        self.db.execute_app(
            "INSERT INTO hop_placements (week_id, trammer_id, entity_id, hop_amount, placed_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(week_id, trammer_id, entity_id) "
            "DO UPDATE SET hop_amount = excluded.hop_amount, placed_at = excluded.placed_at",
            (week.week_id, trammer_id, to_entity_id, new_dest, utcnow()),
        )
        return Placement(
            week_id=week.week_id,
            trammer_id=trammer_id,
            entity_id=to_entity_id,
            hop_amount=new_dest,
        )

    def place_hops(self, trammer_id: str, entity_id: str, amount: float) -> Placement:
        amount = round_hop(amount)
        if amount <= HOP_MIN:
            raise GameError("Le montant doit être positif (2 décimales).")
        week = self.get_current_week()
        self._ensure_invest_window(week)
        self._validate_entity_for_placement(trammer_id, entity_id)
        already = self.placed_this_week(trammer_id, week.week_id)
        self._check_weekly_cap(trammer_id, week.week_id, already + amount)
        existing = self.db.query_app_one(
            "SELECT hop_amount FROM hop_placements WHERE week_id = ? AND trammer_id = ? "
            "AND entity_id = ?",
            (week.week_id, trammer_id, entity_id),
        )
        new_amount = round_hop((existing["hop_amount"] if existing else 0.0) + amount)
        self.db.execute_app(
            "INSERT INTO hop_placements (week_id, trammer_id, entity_id, hop_amount, placed_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(week_id, trammer_id, entity_id) "
            "DO UPDATE SET hop_amount = excluded.hop_amount, placed_at = excluded.placed_at",
            (week.week_id, trammer_id, entity_id, new_amount, utcnow()),
        )
        return Placement(
            week_id=week.week_id,
            trammer_id=trammer_id,
            entity_id=entity_id,
            hop_amount=new_amount,
        )

    def finalize_allocations(self, week_id: str) -> int:
        """Sum placements per entity into entities.hop_allocated (Sunday close)."""
        rows = self.db.query_app(
            "SELECT entity_id, COALESCE(SUM(hop_amount),0) AS total "
            "FROM hop_placements WHERE week_id = ? GROUP BY entity_id",
            (week_id,),
        )
        for r in rows:
            self.db.execute_app(
                "UPDATE entities SET hop_allocated = hop_allocated + ?, updated_at = ? "
                "WHERE id = ?",
                (round_hop(r["total"]), utcnow(), r["entity_id"]),
            )
        self.set_week_status(week_id, "closed")
        return len(rows)

    # ---- recognition ---------------------------------------------------
    def recognize_work(
        self,
        entity_id: str,
        trammer_id: str,
        hops: float,
        description: str | None = None,
        validated: bool = False,
        week_id: str | None = None,
    ):
        hops = round_hop(hops)
        if hops <= HOP_MIN:
            raise GameError("La reconnaissance doit être positive.")
        week_id = week_id or self.get_current_week().week_id
        self.db.execute_app(
            "INSERT INTO hop_recognitions (week_id, entity_id, trammer_id, hop_amount, "
            "description, validated, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (week_id, entity_id, trammer_id, hops, description, 1 if validated else 0, utcnow()),
        )
        if validated:
            self._credit_balance(trammer_id, hops)
            self.db.execute_app(
                "UPDATE game_weeks SET hop_created = hop_created + ? WHERE week_id = ?",
                (hops, week_id),
            )

    def _credit_balance(self, trammer_id: str, hops: float) -> None:
        row = self.db.query_app_one(
            "SELECT hop_balance FROM trammers WHERE discord_user_id = ?", (trammer_id,)
        )
        current = row["hop_balance"] if row else 0.0
        new_balance = min(HOP_MAX_BALANCE, round_hop(current + hops))
        self.db.execute_app(
            "INSERT INTO trammers (discord_user_id, hop_balance, created_at, updated_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(discord_user_id) "
            "DO UPDATE SET hop_balance = ?, updated_at = ?",
            (trammer_id, new_balance, utcnow(), utcnow(), new_balance, utcnow()),
        )

    def get_trammer_balance(self, trammer_id: str) -> float:
        row = self.db.query_app_one(
            "SELECT hop_balance FROM trammers WHERE discord_user_id = ?", (trammer_id,)
        )
        balance = row["hop_balance"] if row else 0.0
        # Enforce GME-5 invariants defensively.
        return round_hop(max(HOP_MIN, min(HOP_MAX_BALANCE, balance)))