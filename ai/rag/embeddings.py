"""Embedding + Chroma vector-store factory (spec §4.4).

Uses Ollama's ``nomic-embed-text`` model by default. The same persist directory
holds all collections (``docs``, ``history``, optional ``web``).
"""

from __future__ import annotations

from functools import lru_cache


def make_embeddings(settings):
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(
        model=settings.embed_model,
        base_url=settings.ollama_host,
    )


@lru_cache(maxsize=8)
def _cached_store(collection: str, chroma_dir: str, embed_model: str, ollama_host: str):
    from langchain_chroma import Chroma
    from langchain_ollama import OllamaEmbeddings

    embeddings = OllamaEmbeddings(model=embed_model, base_url=ollama_host)
    return Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=chroma_dir,
    )


def get_vector_store(settings, collection: str = "docs"):
    """Return a persistent Chroma store for a named collection."""
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    return _cached_store(
        collection,
        str(settings.chroma_dir),
        settings.embed_model,
        settings.ollama_host,
    )
