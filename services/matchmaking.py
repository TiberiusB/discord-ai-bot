"""MatchmakingService (spec §5.2) — surface synergies, propose connections.

v1 matching is keyword overlap over volio labels/details (offers vs
searches/requests), scaled by the other party's trust score. It NEVER acts on a
member's behalf: it returns ``ProposedMatch`` objects and can persist ``Echo``
notifications, but a human always initiates contact (MTM-3, NFR-1).
"""

from __future__ import annotations

import re

from storage.db import Database, utcnow
from storage.models import Echo, ProposedMatch

_WORD_RE = re.compile(r"[\wàâäéèêëîïôöùûüç]+", re.IGNORECASE)
_STOP = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "à", "en", "pour",
    "avec", "the", "a", "of", "and", "to", "for", "je", "tu", "il", "elle",
}

OFFER_KINDS = {"offer", "talent", "interest"}
NEED_KINDS = {"search", "request"}


def _tokens(text: str) -> set[str]:
    return {
        w.lower()
        for w in _WORD_RE.findall(text or "")
        if len(w) > 2 and w.lower() not in _STOP
    }


class MatchmakingService:
    def __init__(self, db: Database, identity, knowledge=None):
        self.db = db
        self.identity = identity
        self.knowledge = knowledge

    def _volios(self, kinds: set[str], exclude_trammer: str | None = None):
        placeholders = ",".join("?" for _ in kinds)
        sql = (
            f"SELECT v.*, t.trust_score FROM volios v "
            f"JOIN trammers t ON t.discord_user_id = v.trammer_id "
            f"WHERE v.active = 1 AND v.kind IN ({placeholders}) "
            f"AND v.visibility IN ('network', 'public')"
        )
        params: list = list(kinds)
        if exclude_trammer:
            sql += " AND v.trammer_id != ?"
            params.append(exclude_trammer)
        return self.db.query_app(sql, tuple(params))

    def find_synergies(self, trammer_id: str, limit: int = 5) -> list[ProposedMatch]:
        """Match this trammer's needs against others' offers and vice versa."""
        my_needs = self.db.query_app(
            "SELECT * FROM volios WHERE trammer_id = ? AND active = 1 AND kind IN "
            "('search', 'request')",
            (trammer_id,),
        )
        my_offers = self.db.query_app(
            "SELECT * FROM volios WHERE trammer_id = ? AND active = 1 AND kind IN "
            "('offer', 'talent', 'interest')",
            (trammer_id,),
        )
        matches: list[ProposedMatch] = []

        others_offers = self._volios(OFFER_KINDS, exclude_trammer=trammer_id)
        for need in my_needs:
            need_tokens = _tokens(f"{need['label']} {need['details'] or ''}")
            for off in others_offers:
                matches.append(
                    self._score(trammer_id, off, need_tokens, off["trust_score"], "wish_offer")
                )

        others_needs = self._volios(NEED_KINDS, exclude_trammer=trammer_id)
        for offer in my_offers:
            offer_tokens = _tokens(f"{offer['label']} {offer['details'] or ''}")
            for need in others_needs:
                matches.append(
                    self._score(trammer_id, need, offer_tokens, need["trust_score"], "skill_need")
                )

        matches = [m for m in matches if m.score > 0]
        matches.sort(key=lambda m: m.score, reverse=True)
        # De-duplicate by other party, keep best.
        seen: set[str] = set()
        unique: list[ProposedMatch] = []
        for m in matches:
            if m.other_id in seen:
                continue
            seen.add(m.other_id)
            unique.append(m)
        return unique[:limit]

    def _score(self, trammer_id, other_row, my_tokens, trust, match_type) -> ProposedMatch:
        other_tokens = _tokens(f"{other_row['label']} {other_row['details'] or ''}")
        overlap = my_tokens & other_tokens
        base = len(overlap) / (len(my_tokens | other_tokens) or 1)
        trust_weight = 0.5 + 0.5 * float(trust or 0.0)
        return ProposedMatch(
            trammer_id=trammer_id,
            other_id=other_row["trammer_id"],
            match_type=match_type,
            score=round(base * trust_weight, 3),
            rationale=(
                f"Termes communs : {', '.join(sorted(overlap)) or '—'} "
                f"(via « {other_row['label']} »)."
            ),
        )

    def create_echo(
        self, recipient_id: str, summary: str, source_id: str | None = None,
        match_type: str = "synergy",
    ) -> Echo:
        cur = self.db.execute_app(
            "INSERT INTO echoes (trammer_id, source_id, match_type, summary, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (recipient_id, source_id, match_type, summary, utcnow()),
        )
        return Echo(
            id=int(cur.lastrowid),
            trammer_id=recipient_id,
            source_id=source_id,
            match_type=match_type,
            summary=summary,
        )

    def list_echoes(self, trammer_id: str, unread_only: bool = False) -> list[Echo]:
        sql = "SELECT * FROM echoes WHERE trammer_id = ?"
        if unread_only:
            sql += " AND read = 0"
        sql += " ORDER BY created_at DESC LIMIT 25"
        rows = self.db.query_app(sql, (trammer_id,))
        return [
            Echo(
                id=r["id"],
                trammer_id=r["trammer_id"],
                source_id=r["source_id"],
                match_type=r["match_type"],
                summary=r["summary"],
                read=bool(r["read"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def mark_echoes_read(self, trammer_id: str) -> None:
        self.db.execute_app(
            "UPDATE echoes SET read = 1 WHERE trammer_id = ?", (trammer_id,)
        )

    def has_recent_echo(self, trammer_id: str, source_id: str, hours: int = 24) -> bool:
        from datetime import datetime, timedelta, timezone

        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        row = self.db.query_app_one(
            "SELECT id FROM echoes WHERE trammer_id = ? AND source_id = ? "
            "AND created_at >= ? LIMIT 1",
            (trammer_id, source_id, since),
        )
        return row is not None

    def propose_echoes_for_all(self, limit_per_trammer: int = 3) -> int:
        """Persist synergy proposals as Echo rows (no DMs). Returns count created."""
        trammers = self.db.query_app(
            "SELECT DISTINCT trammer_id FROM volios WHERE active = 1"
        )
        created = 0
        for row in trammers:
            tid = row["trammer_id"]
            for match in self.find_synergies(tid, limit=limit_per_trammer):
                if self.has_recent_echo(tid, match.other_id):
                    continue
                summary = (
                    f"Synergie possible avec <@{match.other_id}> — {match.rationale}"
                )
                self.create_echo(
                    tid, summary, source_id=match.other_id, match_type=match.match_type
                )
                created += 1
        return created
