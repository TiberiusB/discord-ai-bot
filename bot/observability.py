"""Observability: structured logging + append-only audit trail (spec §10.4, §11.2)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from bot.config import PROJECT_ROOT

AUDIT_PATH = PROJECT_ROOT / "audit.log"

_STD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line (spec §11.2)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def audit(user_id: str, action: str, tool: str | None = None, args: dict | None = None,
          result: str = "ok") -> None:
    """Append an audit record. Arguments are hashed, never stored verbatim."""
    args_hash = ""
    if args:
        raw = json.dumps(args, sort_keys=True, ensure_ascii=False)
        args_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "action": action,
        "tool": tool,
        "args_hash": args_hash,
        "result": result,
    }
    try:
        with AUDIT_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        logging.getLogger("tramice.audit").warning("Could not write audit log")
