"""Curated web source ingestion: same-domain shallow crawl into Chroma ``web``."""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from langchain_core.documents import Document

from ai.rag.embeddings import get_vector_store
from ai.rag.ingest import IngestResult, _splitter
from storage.models import WebSource

log = logging.getLogger("tramice.rag.web_ingest")

_SKIP_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".zip",
    ".mp3", ".mp4", ".avi", ".mov", ".css", ".js", ".ico", ".woff",
    ".woff2", ".ttf", ".eot", ".xml", ".json",
}


class WebIngestError(Exception):
    """Raised when a seed URL fails validation or crawl."""


@dataclass
class CrawlPage:
    url: str
    title: str
    text: str
    depth: int


def normalize_url(url: str) -> str:
    """Strip fragment and normalize scheme/host for deduplication."""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def extract_domain(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_matches_allowlist(host: str, allowlist: list[str]) -> bool:
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    for entry in allowlist:
        entry = str(entry).lower().strip()
        if not entry:
            continue
        if entry.startswith("www."):
            entry = entry[4:]
        if host == entry or host.endswith("." + entry):
            return True
    return False


def _is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_host_ips(hostname: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise WebIngestError(f"Impossible de résoudre le domaine : {hostname}") from exc
    ips: list[str] = []
    for info in infos:
        addr = info[4][0]
        if addr not in ips:
            ips.append(addr)
    return ips


def validate_seed_url(url: str, settings) -> str:
    """Validate and return normalized seed URL; raises WebIngestError on failure."""
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        raise WebIngestError("Seuls les schémas http et https sont autorisés.")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise WebIngestError("URL invalide : hôte manquant.")
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        raise WebIngestError("Les URLs locales ne sont pas autorisées.")
    for ip in _resolve_host_ips(hostname):
        if _is_private_ip(ip):
            raise WebIngestError(
                f"L'hôte {hostname} résout vers une adresse privée ({ip})."
            )
    if settings.get("rag.web.require_allowlist", False):
        allowlist = settings.get("fetch_allowlist", []) or []
        if not allowlist:
            raise WebIngestError(
                "require_allowlist est activé mais fetch_allowlist est vide."
            )
        if not _host_matches_allowlist(hostname, allowlist):
            raise WebIngestError(
                f"Le domaine {hostname} n'est pas dans fetch_allowlist."
            )
    return normalized


def extract_text(html: str, url: str) -> tuple[str, str]:
    """Return (title, plain text) from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url
    if main is None:
        text = soup.get_text(separator="\n", strip=True)
    else:
        text = main.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return title, text


def _same_domain(url: str, seed_domain: str) -> bool:
    host = extract_domain(url)
    return host == seed_domain or host.endswith("." + seed_domain)


def _should_skip_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return True
    path = (parsed.path or "").lower()
    for ext in _SKIP_EXTENSIONS:
        if path.endswith(ext):
            return True
    return False


def _extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = normalize_url(urljoin(base_url, href))
        if absolute not in links:
            links.append(absolute)
    return links


def crawl_same_domain(
    seed_url: str,
    *,
    max_depth: int,
    max_pages: int,
    timeout: float,
    user_agent: str,
) -> list[CrawlPage]:
    """BFS crawl staying on the seed domain."""
    seed_domain = extract_domain(seed_url)
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(seed_url, 0)]
    pages: list[CrawlPage] = []
    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}

    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
    ) as client:
        while queue and len(pages) < max_pages:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            if not _same_domain(url, seed_domain):
                continue
            if _should_skip_url(url):
                continue
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                log.warning("Fetch failed for %s: %s", url, exc)
                continue
            content_type = resp.headers.get("content-type", "").lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                continue
            html = resp.text
            title, text = extract_text(html, url)
            if len(text.strip()) < 50:
                continue
            pages.append(CrawlPage(url=url, title=title, text=text, depth=depth))
            if depth < max_depth:
                for link in _extract_links(html, url):
                    if link not in visited and _same_domain(link, seed_domain):
                        queue.append((link, depth + 1))

    return pages


def delete_web_chunks(settings, seed_url: str) -> int:
    """Delete all Chroma chunks for a given seed URL."""
    store = get_vector_store(settings, "web")
    try:
        result = store.get(where={"seed_url": seed_url})
        ids = result.get("ids", [])
        if ids:
            store.delete(ids=ids)
        return len(ids)
    except Exception:  # noqa: BLE001
        log.exception("Failed to delete web chunks for %s", seed_url)
        return 0


def row_to_web_source(row) -> WebSource:
    return WebSource(
        id=int(row["id"]),
        seed_url=row["seed_url"],
        domain=row["domain"],
        label=row["label"],
        max_depth=int(row["max_depth"]),
        max_pages=int(row["max_pages"]),
        added_by=row["added_by"],
        added_at=row["added_at"],
        last_indexed_at=row["last_indexed_at"],
        last_page_count=int(row["last_page_count"] or 0),
        last_chunk_count=int(row["last_chunk_count"] or 0),
        last_error=row["last_error"],
        active=bool(row["active"]),
    )


def ingest_web_source(settings, source: WebSource) -> IngestResult:
    """Crawl and embed a single curated web source into Chroma ``web``."""
    timeout = float(settings.get("rag.web.fetch_timeout_sec", 15))
    user_agent = settings.get("rag.web.user_agent", "Tramice721-RAG/1.0")
    fetched_at = datetime.now(timezone.utc).isoformat()

    delete_web_chunks(settings, source.seed_url)

    pages = crawl_same_domain(
        source.seed_url,
        max_depth=source.max_depth,
        max_pages=source.max_pages,
        timeout=timeout,
        user_agent=user_agent,
    )
    if not pages:
        raise WebIngestError(
            "Aucune page indexable trouvée (vérifie l'URL et le contenu HTML)."
        )

    documents: list[Document] = []
    for page in pages:
        documents.append(
            Document(
                page_content=page.text,
                metadata={
                    "seed_url": source.seed_url,
                    "source_url": page.url,
                    "title": page.title[:200],
                    "fetched_at": fetched_at,
                    "depth": page.depth,
                },
            )
        )

    splitter = _splitter(
        settings.get("rag.chunk_size", 800),
        settings.get("rag.chunk_overlap", 120),
    )
    chunks = splitter.split_documents(documents)
    store = get_vector_store(settings, "web")
    if chunks:
        store.add_documents(chunks)

    log.info(
        "Ingested web source %s: %d pages -> %d chunks",
        source.seed_url,
        len(pages),
        len(chunks),
    )
    return IngestResult("web", len(pages), len(chunks))


def ingest_all_web_sources(settings, db) -> dict:
    """Re-crawl all active registered web sources."""
    rows = db.list_web_sources(active_only=True)
    results: list[dict] = []
    total_pages = 0
    total_chunks = 0
    errors: list[str] = []

    for row in rows:
        source = row_to_web_source(row)
        try:
            result = ingest_web_source(settings, source)
            db.update_web_source_index_status(
                source.id,
                last_indexed_at=datetime.now(timezone.utc).isoformat(),
                last_page_count=result.documents,
                last_chunk_count=result.chunks,
                last_error=None,
            )
            total_pages += result.documents
            total_chunks += result.chunks
            results.append(
                {
                    "id": source.id,
                    "seed_url": source.seed_url,
                    "pages": result.documents,
                    "chunks": result.chunks,
                    "error": None,
                }
            )
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
            errors.append(f"{source.seed_url}: {err}")
            db.update_web_source_index_status(
                source.id,
                last_error=err[:500],
            )
            results.append(
                {
                    "id": source.id,
                    "seed_url": source.seed_url,
                    "pages": 0,
                    "chunks": 0,
                    "error": err,
                }
            )

    return {
        "sources": len(rows),
        "total_pages": total_pages,
        "total_chunks": total_chunks,
        "errors": errors,
        "details": results,
    }
