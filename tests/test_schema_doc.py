"""docs/design/schema.sql must match what storage/db.py creates."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dump_schema():
    spec = importlib.util.spec_from_file_location("dump_schema", ROOT / "scripts" / "dump_schema.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_schema_doc_is_current():
    dump_schema = _load_dump_schema()
    expected = dump_schema.render()
    actual = (ROOT / "docs" / "design" / "schema.sql").read_text(encoding="utf-8")
    assert actual == expected, "docs/design/schema.sql is stale: run `python scripts/dump_schema.py`"
