"""KnowledgeService (spec §5.7) — grounded retrieval with source attribution.

Every answer carries ``sources`` so the persona can honor NORA / KNW-2 (never
assert what is uncertain; cite where knowledge comes from).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from ai.rag.ingest import ingest_docs
from ai.rag.retriever import semantic_search
from ai.rag.web_ingest import (
    WebIngestError,
    delete_web_chunks,
    extract_domain,
    ingest_all_web_sources,
    ingest_web_source,
    row_to_web_source,
    validate_seed_url,
)
from storage.models import GroundedAnswer, RetrievalChunk, WebSource

log = logging.getLogger("tramice.knowledge")

ReindexScope = Literal["docs", "web", "all"]
DEFAULT_KNOWLEDGE_COLLECTIONS = ["docs", "web"]


class KnowledgeService:
    def __init__(self, settings, db=None):
        self.settings = settings
        self.db = db

    def search(
        self, query: str, collections: list[str] | None = None, k: int = 5
    ) -> list[RetrievalChunk]:
        collections = collections or DEFAULT_KNOWLEDGE_COLLECTIONS
        merged: list[RetrievalChunk] = []
        for collection in collections:
            merged.extend(semantic_search(self.settings, query, collection, k=k))
        merged.sort(key=lambda c: c.score, reverse=True)
        return merged[:k]

    def explain_topic(self, topic: str) -> GroundedAnswer:
        chunks = self.search(topic, collections=["docs", "web"], k=5)
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

    def reindex(self, scope: ReindexScope = "docs") -> dict:
        """Rebuild RAG collections by scope (ADM-2)."""
        result: dict = {"scope": scope}
        if scope in {"docs", "all"}:
            docs_result = ingest_docs(self.settings, reset=True)
            result["docs"] = {
                "collection": docs_result.collection,
                "chunks": docs_result.chunks,
                "documents": docs_result.documents,
            }
        if scope in {"web", "all"}:
            if self.db is None:
                raise RuntimeError("Database required for web reindex.")
            web_result = ingest_all_web_sources(self.settings, self.db)
            result["web"] = web_result
        return result

    def list_web_sources(self) -> list[WebSource]:
        if self.db is None:
            return []
        return [row_to_web_source(row) for row in self.db.list_web_sources()]

    def add_web_source(
        self,
        url: str,
        added_by: str,
        *,
        label: str | None = None,
        max_depth: int | None = None,
        max_pages: int | None = None,
    ) -> dict:
        if self.db is None:
            raise RuntimeError("Database required for web source management.")
        seed_url = validate_seed_url(url, self.settings)
        domain = extract_domain(seed_url)
        depth = max_depth if max_depth is not None else int(
            self.settings.get("rag.web.max_depth", 2)
        )
        pages = max_pages if max_pages is not None else int(
            self.settings.get("rag.web.max_pages", 25)
        )
        source_id = self.db.upsert_web_source(
            seed_url=seed_url,
            domain=domain,
            added_by=added_by,
            label=label,
            max_depth=depth,
            max_pages=pages,
        )
        row = self.db.get_web_source(source_id)
        if row is None:
            raise WebIngestError("Échec d'enregistrement de la source web.")
        source = row_to_web_source(row)
        try:
            ingest_result = ingest_web_source(self.settings, source)
            now = datetime.now(timezone.utc).isoformat()
            self.db.update_web_source_index_status(
                source.id,
                last_indexed_at=now,
                last_page_count=ingest_result.documents,
                last_chunk_count=ingest_result.chunks,
                last_error=None,
            )
            return {
                "id": source.id,
                "seed_url": seed_url,
                "domain": domain,
                "pages": ingest_result.documents,
                "chunks": ingest_result.chunks,
                "label": label,
            }
        except Exception as exc:
            self.db.update_web_source_index_status(
                source.id,
                last_error=str(exc)[:500],
            )
            raise

    def remove_web_source(self, url_or_id: str) -> dict:
        if self.db is None:
            raise RuntimeError("Database required for web source management.")
        seed_url: str | None = None
        source_id: int | None = None
        if url_or_id.isdigit():
            source_id = int(url_or_id)
            row = self.db.get_web_source(source_id)
            if row is None:
                raise WebIngestError(f"Source web #{source_id} introuvable.")
            seed_url = row["seed_url"]
        else:
            seed_url = validate_seed_url(url_or_id, self.settings)
            row = self.db.get_web_source_by_url(seed_url)
            if row is None:
                raise WebIngestError(f"Source web {seed_url} introuvable.")
            source_id = int(row["id"])
        deleted_chunks = delete_web_chunks(self.settings, seed_url)
        self.db.delete_web_source(source_id)
        return {
            "id": source_id,
            "seed_url": seed_url,
            "chunks_deleted": deleted_chunks,
        }

    def web_source_domains(self) -> list[str]:
        """Return domains of active curated web sources (for link allowlist)."""
        return [s.domain for s in self.list_web_sources() if s.domain]
