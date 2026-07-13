"""Service registry: constructs and holds all domain services.

Instantiated once at startup and shared by the Discord layer, the agent tools,
and the scheduler. Services are added as their milestones land.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from storage.db import Database
from storage.history import HistoryStore

if TYPE_CHECKING:  # pragma: no cover
    from services.coordination import CoordinationService
    from services.ecosystem import EcosystemService
    from services.game import GameService
    from services.governance import GovernanceService
    from services.identity import IdentityService
    from services.knowledge import KnowledgeService
    from services.matchmaking import MatchmakingService
    from services.memory import MemoryService


@dataclass
class Services:
    identity: "IdentityService"
    memory: "MemoryService"
    knowledge: "KnowledgeService | None" = None
    matchmaking: "MatchmakingService | None" = None
    coordination: "CoordinationService | None" = None
    ecosystem: "EcosystemService | None" = None
    governance: "GovernanceService | None" = None
    game: "GameService | None" = None


def build_services(settings, db: Database, history: HistoryStore) -> Services:
    from services.identity import IdentityService
    from services.memory import MemoryService

    services = Services(
        identity=IdentityService(db),
        memory=MemoryService(db, history, settings),
    )

    # Knowledge / RAG (M3).
    try:
        from services.knowledge import KnowledgeService

        services.knowledge = KnowledgeService(settings)
    except ImportError:
        pass

    # Community services (M4). Imported defensively so earlier milestones
    # remain runnable before these modules exist.
    try:
        from services.coordination import CoordinationService
        from services.ecosystem import EcosystemService
        from services.governance import GovernanceService
        from services.matchmaking import MatchmakingService

        services.matchmaking = MatchmakingService(db, services.identity, services.knowledge)
        services.coordination = CoordinationService(db)
        services.ecosystem = EcosystemService(db)
        services.governance = GovernanceService(db, history, services.knowledge)
    except ImportError:
        pass

    # Game simulation (M5).
    try:
        from services.game import GameService

        services.game = GameService(db, settings)
    except ImportError:
        pass

    return services
