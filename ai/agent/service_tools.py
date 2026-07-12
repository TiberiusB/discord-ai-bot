"""LangChain tools wrapping the service layer (spec §6.1).

Tools are added per milestone: ``search_knowledge`` (M3); identity /
matchmaking / coordination / ecosystem / governance tools (M4); game tools (M5).
Each tool returns a short French-friendly string for the agent to relay.

Mutating tools (place HOPs, propose events, open votes) are NOT exposed as
free-acting agent tools — they run through slash commands with a confirmation
UI so a human always approves (NFR-1, MTM-3, GOV-2).
"""

from __future__ import annotations

import logging

from langchain_core.tools import StructuredTool

log = logging.getLogger("tramice.service_tools")


def make_service_tools(settings, services) -> list:
    tools: list = []

    # ---- Knowledge (M3) ------------------------------------------------
    if getattr(services, "knowledge", None) is not None:
        knowledge = services.knowledge

        def search_knowledge(query: str) -> str:
            """Recherche dans les documents du projet (jeu, règles, HOP, carnets)."""
            chunks = knowledge.search(query, collections=["docs"], k=4)
            if not chunks:
                return "Aucune source trouvée dans les documents."
            return "\n\n".join(
                f"[source: {c.source}] {c.text[:500]}" for c in chunks
            )

        tools.append(
            StructuredTool.from_function(
                func=search_knowledge,
                name="search_knowledge",
                description=(
                    "Rechercher des informations factuelles sur La Guilde des "
                    "Tramarades, les règles du jeu, les HOP, le cycle hebdomadaire "
                    "et les carnets, à partir des documents du projet. À utiliser "
                    "avant d'affirmer un fait sur le jeu. Retourne des extraits avec "
                    "leur source."
                ),
            )
        )

    # ---- Community + game tools (M4/M5) --------------------------------
    try:
        from ai.agent.community_tools import make_community_tools

        tools.extend(make_community_tools(settings, services))
    except ImportError:
        pass

    log.info("Built %d service tools", len(tools))
    return tools
