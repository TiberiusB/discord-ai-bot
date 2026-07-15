"""Tests for web URL validation, domain rules, and crawl helpers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ai.rag.web_ingest import (
    WebIngestError,
    _same_domain,
    _should_skip_url,
    extract_domain,
    normalize_url,
    validate_seed_url,
)
from bot.config import Settings, PROJECT_ROOT


@pytest.fixture
def web_settings(tmp_path) -> Settings:
    raw = {
        "fetch_allowlist": ["latramice.net"],
        "rag": {
            "web": {"require_allowlist": False},
        },
    }
    return Settings(
        raw=raw,
        data_dir=tmp_path / "data",
        project_root=PROJECT_ROOT,
        docs_dir=PROJECT_ROOT / "docs",
        prompts_dir=PROJECT_ROOT / "prompts",
    )


def test_normalize_url_strips_fragment_and_www() -> None:
    assert (
        normalize_url("https://www.Example.com/path/page#section")
        == "https://example.com/path/page"
    )


def test_extract_domain() -> None:
    assert extract_domain("https://www.latramice.net/foo") == "latramice.net"


def test_same_domain_accepts_subdomain() -> None:
    assert _same_domain("https://blog.latramice.net/a", "latramice.net") is True
    assert _same_domain("https://other.net/a", "latramice.net") is False


def test_should_skip_non_html_extensions() -> None:
    assert _should_skip_url("https://latramice.net/file.pdf") is True
    assert _should_skip_url("https://latramice.net/about") is False


@patch("ai.rag.web_ingest._resolve_host_ips", return_value=["93.184.216.34"])
def test_validate_seed_url_accepts_public_host(_mock, web_settings: Settings) -> None:
    url = validate_seed_url("https://latramice.net/boutique/", web_settings)
    assert url == "https://latramice.net/boutique"


@patch("ai.rag.web_ingest._resolve_host_ips", return_value=["127.0.0.1"])
def test_validate_seed_url_rejects_private_ip(_mock, web_settings: Settings) -> None:
    with pytest.raises(WebIngestError, match="privée"):
        validate_seed_url("https://evil.example.com/", web_settings)


@patch("ai.rag.web_ingest._resolve_host_ips", return_value=["93.184.216.34"])
def test_validate_seed_url_rejects_localhost(_mock, web_settings: Settings) -> None:
    with pytest.raises(WebIngestError, match="locales"):
        validate_seed_url("http://localhost:8080/", web_settings)


@patch("ai.rag.web_ingest._resolve_host_ips", return_value=["169.254.169.254"])
def test_validate_seed_url_rejects_metadata_ip(_mock, web_settings: Settings) -> None:
    with pytest.raises(WebIngestError, match="privée"):
        validate_seed_url("http://169.254.169.254/latest/", web_settings)


@patch("ai.rag.web_ingest._resolve_host_ips", return_value=["93.184.216.34"])
def test_validate_seed_url_enforces_allowlist_when_required(
    _mock, web_settings: Settings
) -> None:
    web_settings.raw["rag"]["web"]["require_allowlist"] = True
    validate_seed_url("https://latramice.net/", web_settings)
    with pytest.raises(WebIngestError, match="fetch_allowlist"):
        validate_seed_url("https://example.com/", web_settings)
