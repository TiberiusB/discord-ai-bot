"""KnowledgeService (spec §5.7) — grounded retrieval with source attribution.

Every answer carries ``sources`` so the persona can honor NORA / KNW-2 (never
assert what is uncertain; cite where knowledge comes from).
"""

from __future__ import annotations

import logging

from ai.rag.ingest import ingest_docs
from ai.rag.retriever import semantic_search
from storage.models import GroundedAnswer, RetrievalChunk

log = logging.getLogger("tramice.knowledge")


class KnowledgeService:
    def __init__(self, settings):
        self.settings = settings

    def search(
        self, query: str, collections: list[str] | None = None, k: int = 5
    ) -> list[RetrievalChunk]:
        collections = collections or self.settings.get("rag.collections", ["docs"])
        merged: list[RetrievalChunk] = []
        for collection in collections:
            merged.extend(semantic_search(self.settings, query, collection, k=k))
        merged.sort(key=lambda c: c.score, reverse=True)
        return merged[:k]

    def explain_topic(self, topic: str) -> GroundedAnswer:
        chunks = self.search(topic, collections=["docs"], k=5)
        if not chunks:
            return GroundedAnswer(
                answer=(
                    "Je n'ai pas trouvé de source fiable — voici ce que je peux dire "
                    "avec prudence : je n'ai pas de document sur ce sujet pour l'instant."
                ),
                sources=[],
            )
        body = "\n\n".join(
            f"[{c.source}] {c.text[:600]}" for c in chunks
        )
        return GroundedAnswer(answer=body, sources=chunks)

    def reindex(self) -> dict:
        """Rebuild the ``docs`` collection from ``docs/`` (ADM-2)."""
        result = ingest_docs(self.settings, reset=True)
        return {"collection": result.collection, "chunks": result.chunks,
                "documents": result.documents}
