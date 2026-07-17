"""Configuration loader: merges `config.yaml` with `.env` secrets.

Exposes a single `Settings` object (via `load_settings`) that the rest of the
app reads. Values from `config.yaml` are the defaults; environment variables
supply secrets and deployment-specific IDs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"
PROMPTS_DIR = PROJECT_ROOT / "prompts"


def _split_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass
class Settings:
    """Resolved configuration for a running bot process."""

    # Raw merged config tree (from config.yaml).
    raw: dict[str, Any] = field(default_factory=dict)

    # Secrets / environment.
    discord_token: str = ""
    ollama_host: str = "http://127.0.0.1:11434"
    guild_id: str | None = None
    admin_role_ids: list[str] = field(default_factory=list)
    architecture_role_ids: list[str] = field(default_factory=list)

    # Paths.
    project_root: Path = PROJECT_ROOT
    data_dir: Path = DATA_DIR
    docs_dir: Path = DOCS_DIR
    prompts_dir: Path = PROMPTS_DIR

    # ---- convenience accessors ----------------------------------------
    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Fetch a nested config value, e.g. ``get("llm.model")``."""
        node: Any = self.raw
        for part in dotted_key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    @property
    def bot_name(self) -> str:
        return self.get("bot.name", "Tramice721")

    @property
    def prefix(self) -> str:
        return self.get("bot.prefix", "!ai")

    @property
    def locale_default(self) -> str:
        return self.get("bot.locale_default", "fr")

    @property
    def timezone(self) -> str:
        return self.get("bot.timezone", "America/Montreal")

    @property
    def model(self) -> str:
        return self.get("llm.model", "qwen2.5:7b-instruct")

    @property
    def temperature(self) -> float:
        return float(self.get("llm.temperature", 0.7))

    @property
    def max_tokens(self) -> int:
        return int(self.get("llm.max_tokens", 2048))

    @property
    def embed_model(self) -> str:
        return self.get("llm.embed_model", "nomic-embed-text")

    @property
    def summary_channel_id(self) -> str | None:
        val = self.get("channels.summary_channel_id")
        return str(val) if val not in (None, "", "null") else None

    # DB / vector store paths (kept in one place).
    @property
    def app_db_path(self) -> Path:
        return self.data_dir / "app.sqlite"

    @property
    def history_db_path(self) -> Path:
        return self.data_dir / "history.sqlite"

    @property
    def checkpoints_db_path(self) -> Path:
        return self.data_dir / "checkpoints.sqlite"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"


def load_settings(config_path: Path | None = None) -> Settings:
    """Load `.env` then `config.yaml` into a `Settings` object."""
    load_dotenv(PROJECT_ROOT / ".env")

    config_path = config_path or (PROJECT_ROOT / "config.yaml")
    raw: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

    settings = Settings(
        raw=raw,
        discord_token=os.getenv("DISCORD_TOKEN", ""),
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        guild_id=os.getenv("GUILD_ID") or None,
        admin_role_ids=_split_ids(os.getenv("ADMIN_ROLE_IDS")),
        architecture_role_ids=_split_ids(os.getenv("ARCHITECTURE_ROLE_IDS")),
    )

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
