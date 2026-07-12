"""Retrieval over Chroma collections (spec §6.3)."""

from __future__ import annotations

import logging

from ai.rag.embeddings import get_vector_store
from storage.models import RetrievalChunk

log = logging.getLogger("tramice.rag.retriever")


def semantic_search(
    settings, query: str, collection: str = "docs", k: int = 5
) -> list[RetrievalChunk]:
    """Vector similarity search; returns scored chunks with source metadata."""
    store = get_vector_store(settings, collection)
    try:
        results = store.similarity_search_with_relevance_scores(query, k=k)
    except Exception:  # noqa: BLE001 - e.g. Ollama down or empty collection
        log.exception("semantic_search failed (collection=%s)", collection)
        return []
    chunks: list[RetrievalChunk] = []
    for doc, score in results:
        meta = dict(doc.metadata or {})
        source = meta.get("source") or meta.get("channel_id") or collection
        chunks.append(
            RetrievalChunk(
                text=doc.page_content,
                source=str(source),
                score=float(score),
                metadata=meta,
            )
        )
    return chunks
