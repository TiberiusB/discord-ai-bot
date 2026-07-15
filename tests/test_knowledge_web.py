"""Tests for KnowledgeService web source management."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bot.config import Settings, PROJECT_ROOT
from services.knowledge import KnowledgeService
from storage.db import build_database


@pytest.fixture
def knowledge_setup(tmp_path):
    raw = {
        "social_norms_defaults": {},
        "rag": {
            "chunk_size": 800,
            "chunk_overlap": 120,
            "web": {"max_depth": 1, "max_pages": 5, "require_allowlist": False},
        },
    }
    settings = Settings(
        raw=raw,
        data_dir=tmp_path / "data",
        project_root=PROJECT_ROOT,
        docs_dir=PROJECT_ROOT / "docs",
        prompts_dir=PROJECT_ROOT / "prompts",
    )
    db = build_database(settings)
    ks = KnowledgeService(settings, db)
    yield ks, db, settings
    db.close()


@patch("ai.rag.web_ingest._resolve_host_ips", return_value=["93.184.216.34"])
@patch("services.knowledge.ingest_web_source")
def test_add_web_source_updates_registry(mock_ingest, _mock_dns, knowledge_setup) -> None:
    ks, db, _settings = knowledge_setup
    from ai.rag.ingest import IngestResult

    mock_ingest.return_value = IngestResult("web", 3, 12)
    result = ks.add_web_source(
        "https://latramice.net/test/",
        "admin-1",
        label="Test",
    )
    assert result["pages"] == 3
    assert result["chunks"] == 12
    sources = ks.list_web_sources()
    assert len(sources) == 1
    assert sources[0].label == "Test"
    assert sources[0].last_page_count == 3
    assert sources[0].last_chunk_count == 12


@patch("services.knowledge.delete_web_chunks", return_value=5)
def test_remove_web_source_deletes_registry(mock_delete, knowledge_setup) -> None:
    ks, db, _settings = knowledge_setup
    db.upsert_web_source(
        seed_url="https://latramice.net/removed/",
        domain="latramice.net",
        added_by="admin",
        label="Gone",
    )
    with patch("services.knowledge.validate_seed_url", return_value="https://latramice.net/removed/"):
        result = ks.remove_web_source("https://latramice.net/removed/")
    assert result["chunks_deleted"] == 5
    assert ks.list_web_sources() == []
    mock_delete.assert_called_once()


@patch("services.knowledge.ingest_docs")
@patch("services.knowledge.ingest_all_web_sources")
def test_reindex_scope_dispatches(mock_web, mock_docs, knowledge_setup) -> None:
    ks, _db, _settings = knowledge_setup
    from ai.rag.ingest import IngestResult

    mock_docs.return_value = IngestResult("docs", 2, 10)
    mock_web.return_value = {
        "sources": 1,
        "total_pages": 4,
        "total_chunks": 20,
        "errors": [],
        "details": [],
    }

    docs_only = ks.reindex("docs")
    assert "docs" in docs_only
    assert "web" not in docs_only
    mock_docs.assert_called_once()
    mock_docs.reset_mock()

    web_only = ks.reindex("web")
    assert "web" in web_only
    assert "docs" not in web_only
    mock_web.assert_called_once()
    mock_web.reset_mock()

    both = ks.reindex("all")
    assert "docs" in both and "web" in both
    mock_docs.assert_called_once()
    mock_web.assert_called_once()


def test_search_defaults_include_docs_and_web(knowledge_setup) -> None:
    ks, _db, _settings = knowledge_setup
    with patch("services.knowledge.semantic_search") as mock_search:
        mock_search.return_value = []
        ks.search("HOP")
        assert mock_search.call_count == 2
        collections = [call.args[2] for call in mock_search.call_args_list]
        assert collections == ["docs", "web"]
