"""Read-only community tools for the agent (spec §6.1, M4).

These tools give the agent awareness of the ecosystem and governance state
without needing the requester's identity, so the model cannot accidentally act
on the wrong user. All mutations (volio edits, HOP placement, events, votes)
run through slash commands with a confirmation UI (NFR-1, MTM-3, GOV-2).
"""

from __future__ import annotations

import logging

from langchain_core.tools import StructuredTool

log = logging.getLogger("tramice.community_tools")


def make_community_tools(settings, services) -> list:
    tools: list = []
    if services is None:
        return tools

    ecosystem = getattr(services, "ecosystem", None)
    governance = getattr(services, "governance", None)

    if ecosystem is not None:
        from services.ecosystem import MondoFilters

        def list_mondo(view: str = "cosmo", kind: str = "") -> str:
            """Lister le Mondo (carte des entreprises, quêtes, missions, lieux)."""
            view = view if view in {"perso", "cosmo"} else "cosmo"
            filters = MondoFilters(kind=kind or None, limit=12)
            entities = ecosystem.list_mondo(view, None, filters)
            if not entities:
                return "Le Mondo est encore vide — aucune entité enregistrée."
            return "\n".join(
                f"- [{e.kind}] {e.title} (phase: {e.phase}, HOP demandés: "
                f"{e.hop_requested:.2f})"
                for e in entities
            )

        def get_playtest_stats() -> str:
            """Statistiques du playtest : nombre d'entités par type et de trammers."""
            stats = ecosystem.get_playtest_stats()
            by_kind = ", ".join(f"{k}: {n}" for k, n in stats["entities_by_kind"].items())
            return f"Trammers : {stats['trammers']}. Entités — {by_kind or 'aucune'}."

        tools += [
            StructuredTool.from_function(
                func=list_mondo,
                name="list_mondo",
                description=(
                    "Afficher un aperçu du Mondo (entreprises, quêtes, missions, "
                    "lieux, événements). view='perso' ou 'cosmo'; kind facultatif "
                    "(enterprise|quest|mission|event|place|idea)."
                ),
            ),
            StructuredTool.from_function(
                func=get_playtest_stats,
                name="get_playtest_stats",
                description="Obtenir les statistiques globales du playtest.",
            ),
        ]

    if governance is not None:

        def list_open_votes() -> str:
            """Lister les votes ouverts de la communauté."""
            votes = governance.list_open_votes()
            if not votes:
                return "Aucun vote ouvert pour le moment."
            return "\n".join(
                f"- « {v.title} » (seuil {int(v.threshold * 100)}%)" for v in votes
            )

        def get_social_norms() -> str:
            """Afficher les normes sociales en vigueur (ce qui est public/privé)."""
            norms = governance.get_social_norms()
            if not norms:
                return "Aucune norme sociale définie."
            return "\n".join(f"- {k}: {v}" for k, v in norms.items())

        tools += [
            StructuredTool.from_function(
                func=list_open_votes,
                name="list_open_votes",
                description="Lister les votes ouverts.",
            ),
            StructuredTool.from_function(
                func=get_social_norms,
                name="get_social_norms",
                description="Afficher les normes sociales en vigueur.",
            ),
        ]

    return tools
