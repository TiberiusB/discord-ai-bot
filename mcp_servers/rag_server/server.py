"""MCP server: rag_server (spec §6.3).

Exposes semantic search over the Chroma vector store as a stdio MCP tool.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from ai.rag.retriever import semantic_search  # noqa: E402
from bot.config import load_settings  # noqa: E402

mcp = FastMCP("rag_server")
_settings = load_settings()


def _search(query: str, collection: str, k: int) -> list[dict]:
    if collection == "all":
        chunks = semantic_search(_settings, query, "docs", k=k)
        web_chunks = semantic_search(_settings, query, "web", k=k)
        merged = sorted(chunks + web_chunks, key=lambda c: c.score, reverse=True)
        chunks = merged[:k]
    else:
        chunks = semantic_search(_settings, query, collection=collection, k=k)
    return [
        {"text": c.text, "source": c.source, "score": c.score, "metadata": c.metadata}
        for c in chunks
    ]


@mcp.tool()
def semantic_search_docs(query: str, collection: str = "docs", k: int = 5) -> list[dict]:
    """Recherche vectorielle (docs, web, history, ou all pour docs+web)."""
    return _search(query, collection, k)


if __name__ == "__main__":
    mcp.run(transport="stdio")
