"""GovernanceService (spec §5.6) — norms, votes, summaries, signalements, juries.

Decision/vote/transaction actions never happen autonomously (GOV-2): this
service records ballots that humans cast and tallies them against a threshold.
"""

from __future__ import annotations

import json
import random
import uuid
from collections import Counter
from dataclasses import dataclass

from storage.db import Database, utcnow
from storage.history import HistoryStore
from storage.models import Summary, Vote


@dataclass
class VoteSpec:
    title: str
    description: str | None = None
    threshold: float = 0.80
    closes_at: str | None = None


@dataclass
class SignalementSpec:
    target_id: str | None
    level: int  # 1=discomfort, 2=breach, 3=danger
    description: str


@dataclass
class BallotResult:
    vote_id: str
    yes: int
    no: int
    abstain: int
    ratio: float
    passed: bool
    threshold: float


@dataclass
class ModerationSuggestion:
    target_id: str
    open_count: int
    level3_count: int
    action: str
    reasons: list[str]
    message: str


class GovernanceService:
    def __init__(self, db: Database, history: HistoryStore, knowledge=None, settings=None):
        self.db = db
        self.history = history
        self.knowledge = knowledge
        self.settings = settings

    # ---- social norms (GOV-10..12) ------------------------------------
    def get_social_norms(self) -> dict:
        norms: dict = {}
        for row in self.db.query_app("SELECT key, value FROM social_norms"):
            try:
                norms[row["key"]] = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                norms[row["key"]] = row["value"]
        return norms

    def set_social_norm(self, admin_id: str, key: str, value) -> None:
        self.db.execute_app(
            "INSERT INTO social_norms (key, value, updated_by, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
            (key, json.dumps(value), admin_id, utcnow()),
        )

    # ---- votes (GOV-1) -------------------------------------------------
    def create_vote(self, creator_id: str, spec: VoteSpec) -> Vote:
        vote_id = str(uuid.uuid4())
        now = utcnow()
        self.db.execute_app(
            "INSERT INTO votes (id, title, description, threshold, created_by, "
            "status, closes_at, created_at) VALUES (?, ?, ?, ?, ?, 'open', ?, ?)",
            (vote_id, spec.title, spec.description, spec.threshold, creator_id,
             spec.closes_at, now),
        )
        return Vote(
            id=vote_id,
            title=spec.title,
            description=spec.description,
            threshold=spec.threshold,
            created_by=creator_id,
            status="open",
            closes_at=spec.closes_at,
            created_at=now,
        )

    def cast_ballot(self, vote_id: str, trammer_id: str, choice: str) -> BallotResult:
        if choice not in {"yes", "no", "abstain"}:
            raise ValueError("choice must be yes|no|abstain")
        self.db.execute_app(
            "INSERT INTO vote_ballots (vote_id, trammer_id, choice, cast_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(vote_id, trammer_id) "
            "DO UPDATE SET choice = excluded.choice, cast_at = excluded.cast_at",
            (vote_id, trammer_id, choice, utcnow()),
        )
        return self.tally(vote_id)

    def tally(self, vote_id: str) -> BallotResult:
        vote = self.db.query_app_one("SELECT * FROM votes WHERE id = ?", (vote_id,))
        threshold = vote["threshold"] if vote else 0.80
        rows = self.db.query_app(
            "SELECT choice, COUNT(*) AS n FROM vote_ballots WHERE vote_id = ? GROUP BY choice",
            (vote_id,),
        )
        counts = {r["choice"]: r["n"] for r in rows}
        yes = counts.get("yes", 0)
        no = counts.get("no", 0)
        abstain = counts.get("abstain", 0)
        decisive = yes + no
        ratio = (yes / decisive) if decisive else 0.0
        passed = decisive > 0 and ratio >= threshold
        return BallotResult(vote_id, yes, no, abstain, round(ratio, 3), passed, threshold)

    def list_open_votes(self) -> list[Vote]:
        rows = self.db.query_app(
            "SELECT * FROM votes WHERE status = 'open' ORDER BY created_at DESC LIMIT 25"
        )
        return [
            Vote(
                id=r["id"], title=r["title"], description=r["description"],
                threshold=r["threshold"], created_by=r["created_by"],
                status=r["status"], closes_at=r["closes_at"], created_at=r["created_at"],
            )
            for r in rows
        ]

    # ---- summaries (GOV-4) --------------------------------------------
    def collect_channel_text(self, channel_id: str, since: str, until: str) -> tuple[str, int]:
        rows = self.history.fetch_channel_between(channel_id, since, until, include_dm=False)
        lines = [f"{r['user_name'] or r['user_id']}: {r['content']}" for r in rows]
        return "\n".join(lines), len(rows)

    def summarize_channel(self, channel_id: str, since: str, until: str) -> Summary:
        """Deterministic extractive summary (participants + volume).

        Richer narrative summaries are produced by the LLM via the agent tool
        or the daily-summary job; this method needs no model and is testable.
        """
        rows = self.history.fetch_channel_between(channel_id, since, until, include_dm=False)
        if not rows:
            return Summary(
                title="Résumé du salon",
                body="Aucun message dans cette période.",
                message_count=0,
                period=f"{since} → {until}",
            )
        participants = Counter(r["user_name"] or r["user_id"] for r in rows)
        top = ", ".join(f"{name} ({n})" for name, n in participants.most_common(5))
        body = (
            f"{len(rows)} messages de {len(participants)} participant·e·s.\n"
            f"Plus actif·ve·s : {top}."
        )
        return Summary(
            title="Résumé du salon",
            body=body,
            message_count=len(rows),
            period=f"{since} → {until}",
        )

    # ---- conflict resolution (GOV-7..9) -------------------------------
    def file_signalement(self, reporter_id: str, spec: SignalementSpec) -> int:
        level = max(1, min(3, int(spec.level)))
        cur = self.db.execute_app(
            "INSERT INTO signalements (reporter_id, target_id, level, description, "
            "status, created_at) VALUES (?, ?, ?, ?, 'open', ?)",
            (reporter_id, spec.target_id, level, spec.description, utcnow()),
        )
        return int(cur.lastrowid)

    def evaluate_moderation(self, target_id: str | None) -> ModerationSuggestion | None:
        """Suggest suspend/ban to admins when signalement thresholds are crossed."""
        if not target_id:
            return None
        threshold = 3
        if self.settings is not None:
            threshold = int(self.settings.get("governance.escalation_threshold", 3))

        rows = self.db.query_app(
            "SELECT level, description FROM signalements "
            "WHERE target_id = ? AND status = 'open'",
            (target_id,),
        )
        if not rows:
            return None

        open_count = len(rows)
        level3_count = sum(1 for r in rows if int(r["level"]) >= 3)
        norms = self.get_social_norms()
        reasons: list[str] = []
        if level3_count:
            reasons.append(f"{level3_count} signalement(s) de niveau 3 (danger immédiat).")
        if open_count >= threshold:
            reasons.append(f"{open_count} signalement(s) ouverts (seuil {threshold}).")
        if norms.get("dm_always_private"):
            reasons.append("Norme : les DM restent privés — vérifier les fuites de confidences.")
        if norms.get("confidences_never_shared"):
            reasons.append("Norme : les confidences ne doivent jamais être partagées.")

        if level3_count >= 1:
            action = "suspendre ou bannir"
        elif open_count >= threshold:
            action = "suspendre temporairement ou médiation renforcée"
        else:
            return None

        excerpts = [r["description"][:120] for r in rows[:3]]
        message = (
            f"**Suggestion de modération (Tramice721 ne peut pas agir seule)**\n"
            f"Membre ciblé : <@{target_id}>\n"
            f"Action suggérée : {action}\n"
            f"Raisons :\n"
            + "\n".join(f"- {r}" for r in reasons)
            + "\nExtraits récents :\n"
            + "\n".join(f"- {e}" for e in excerpts)
            + "\nDécision humaine requise (GOV-2)."
        )
        return ModerationSuggestion(
            target_id=target_id,
            open_count=open_count,
            level3_count=level3_count,
            action=action,
            reasons=reasons,
            message=message,
        )

    def open_tribunal(self, signalement_id: int) -> str:
        tribunal_id = str(uuid.uuid4())
        self.db.execute_app(
            "INSERT INTO tribunals (id, signalement_id, status, created_at) "
            "VALUES (?, ?, 'mediation', ?)",
            (tribunal_id, signalement_id, utcnow()),
        )
        return tribunal_id

    def draw_jury(
        self, tribunal_id: str, pool_guild_id: str | None = None, size: int = 7,
        conflicted: list[str] | None = None, seed: int | None = None,
    ) -> list[str]:
        """Uniform random jury from active trammers, excluding conflicted parties.

        The RNG seed is recorded (spec §5.6) so a draw can be audited/reproduced.
        """
        conflicted = set(conflicted or [])
        rows = self.db.query_app("SELECT discord_user_id FROM trammers")
        pool = [r["discord_user_id"] for r in rows if r["discord_user_id"] not in conflicted]
        if seed is None:
            seed = random.randrange(2**32)
        rng = random.Random(seed)
        rng.shuffle(pool)
        jurors = pool[: min(size, len(pool))]
        now = utcnow()
        for juror in jurors:
            self.db.execute_app(
                "INSERT OR IGNORE INTO tribunal_jurors (tribunal_id, trammer_id, selected_at) "
                "VALUES (?, ?, ?)",
                (tribunal_id, juror, now),
            )
        self.db.execute_app(
            "UPDATE tribunals SET status = 'jury' WHERE id = ?", (tribunal_id,)
        )
        # Record the seed in jurisprudence-adjacent audit trail via decision note.
        self.db.execute_app(
            "UPDATE tribunals SET decision = ? WHERE id = ?",
            (json.dumps({"jury_seed": seed}), tribunal_id),
        )
        return jurors

    def record_jurisprudence(self, tribunal_id: str, summary: str) -> None:
        self.db.execute_app(
            "INSERT INTO jurisprudence (tribunal_id, summary, created_at) VALUES (?, ?, ?)",
            (tribunal_id, summary, utcnow()),
        )
        self.db.execute_app(
            "UPDATE tribunals SET status = 'closed' WHERE id = ?", (tribunal_id,)
        )
