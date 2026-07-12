"""Ingestion pipeline (spec §4.4): docs and message history into Chroma.

``docs`` collection: PDF + Markdown from ``docs/`` (~800-token chunks).
``history`` collection: logged messages (~400-token chunks), used by the
nightly indexing job (M5). DMs / confidences are excluded (privacy by policy).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ai.rag.embeddings import get_vector_store

log = logging.getLogger("tramice.rag.ingest")

# Approximate chars-per-token so config token targets map to the char splitter.
CHARS_PER_TOKEN = 4


@dataclass
class IngestResult:
    collection: str
    documents: int
    chunks: int


def _splitter(chunk_tokens: int, overlap_tokens: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_tokens * CHARS_PER_TOKEN,
        chunk_overlap=overlap_tokens * CHARS_PER_TOKEN,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def _read_pdf(path: Path) -> list[Document]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    docs: list[Document] = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            docs.append(
                Document(
                    page_content=text,
                    metadata={"source": path.name, "page": page_num},
                )
            )
    return docs


def _read_markdown(path: Path) -> list[Document]:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []
    return [Document(page_content=text, metadata={"source": path.name, "page": 0})]


def load_docs(docs_dir: Path) -> list[Document]:
    """Load PDFs and Markdown files from ``docs/`` into LangChain Documents."""
    documents: list[Document] = []
    if not docs_dir.exists():
        return documents
    for path in sorted(docs_dir.iterdir()):
        suffix = path.suffix.lower()
        try:
            if suffix == ".pdf":
                documents.extend(_read_pdf(path))
            elif suffix in {".md", ".txt"}:
                documents.extend(_read_markdown(path))
        except Exception:  # noqa: BLE001
            log.exception("Failed to read %s", path)
    return documents


def _reset_collection(settings, collection: str) -> None:
    """Drop existing vectors so re-ingestion does not duplicate content."""
    store = get_vector_store(settings, collection)
    try:
        store.reset_collection()
    except Exception:  # noqa: BLE001 - older Chroma may lack reset_collection
        try:
            ids = store.get().get("ids", [])
            if ids:
                store.delete(ids=ids)
        except Exception:  # noqa: BLE001
            log.warning("Could not reset collection %s", collection)


def ingest_docs(settings, reset: bool = True) -> IngestResult:
    """Ingest ``docs/`` into the ``docs`` Chroma collection (KNW-1)."""
    documents = load_docs(settings.docs_dir)
    splitter = _splitter(
        settings.get("rag.chunk_size", 800), settings.get("rag.chunk_overlap", 120)
    )
    chunks = splitter.split_documents(documents)
    if reset:
        _reset_collection(settings, "docs")
    store = get_vector_store(settings, "docs")
    if chunks:
        store.add_documents(chunks)
    log.info("Ingested %d docs -> %d chunks (docs)", len(documents), len(chunks))
    return IngestResult("docs", len(documents), len(chunks))


def ingest_history_rows(settings, rows) -> IngestResult:
    """Embed message rows into the ``history`` collection (spec §4.4).

    ``rows`` are ``sqlite3.Row`` objects from ``history.fetch_unindexed``. DMs
    are already excluded by the caller (privacy by policy).
    """
    splitter = _splitter(400, 60)
    documents: list[Document] = []
    for r in rows:
        content = (r["content"] or "").strip()
        if not content:
            continue
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "channel_id": r["channel_id"],
                    "user_id": r["user_id"],
                    "created_at": r["created_at"],
                    "message_id": r["id"],
                },
            )
        )
    chunks = splitter.split_documents(documents)
    store = get_vector_store(settings, "history")
    if chunks:
        store.add_documents(chunks)
    log.info("Ingested %d messages -> %d chunks (history)", len(documents), len(chunks))
    return IngestResult("history", len(documents), len(chunks))


if __name__ == "__main__":  # `python -m ai.rag.ingest` rebuilds the docs index.
    import logging as _logging
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    _logging.basicConfig(level=_logging.INFO)
    from bot.config import load_settings

    _settings = load_settings()
    _result = ingest_docs(_settings, reset=True)
    print(
        f"Ingested {_result.documents} documents into "
        f"{_result.chunks} chunks (collection: {_result.collection})."
    )
