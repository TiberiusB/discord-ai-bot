"""Privacy helpers for RAG history embeddings (MEM-2)."""

from __future__ import annotations

import logging

from ai.rag.embeddings import get_vector_store

log = logging.getLogger("tramice.rag.privacy")

PUBLIC_COLLECTIONS = ("docs", "web")


def public_collections() -> tuple[str, ...]:
    """Collections safe for public /mondo knowledge browse (never DM history)."""
    return PUBLIC_COLLECTIONS


def delete_user_history_embeddings(settings, user_id: str) -> int:
    """Remove ``history`` collection vectors tagged with ``user_id`` metadata."""
    try:
        store = get_vector_store(settings, "history")
        collection = store._collection  # noqa: SLF001 - Chroma API
        # Chroma metadata filter syntax.
        result = collection.delete(where={"user_id": user_id})
        deleted = len(result) if isinstance(result, list) else 0
        log.info("Deleted %d history embeddings for user=%s", deleted, user_id)
        return deleted
    except Exception:  # noqa: BLE001
        log.exception("Failed to delete history embeddings for user=%s", user_id)
        return 0
