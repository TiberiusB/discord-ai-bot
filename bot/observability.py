"""Observability: structured logging + append-only audit trail (spec §10.4, §11.2)."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bot.config import PROJECT_ROOT

AUDIT_PATH = PROJECT_ROOT / "audit.log"
HEALTH_PATH = PROJECT_ROOT / "data" / ".health"

_STD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime"}

_turn_log = logging.getLogger("tramice.turn")
_job_log = logging.getLogger("tramice.job")

# In-memory runtime error counters for /health (not persisted).
_last_event_error: str | None = None
_last_event_error_at: str | None = None
_last_job_error_id: str | None = None
_last_job_error_at: str | None = None
_event_error_count: int = 0
_job_error_count: int = 0


def record_event_error(event: str, summary: str) -> None:
    global _last_event_error, _last_event_error_at, _event_error_count
    _last_event_error = f"{event}: {summary}"
    _last_event_error_at = datetime.now(timezone.utc).isoformat()
    _event_error_count += 1


def record_job_error(job_id: str) -> None:
    global _last_job_error_id, _last_job_error_at, _job_error_count
    _last_job_error_id = job_id
    _last_job_error_at = datetime.now(timezone.utc).isoformat()
    _job_error_count += 1


def get_runtime_health() -> dict[str, Any]:
    return {
        "last_event_error": _last_event_error,
        "last_event_error_at": _last_event_error_at,
        "last_job_error_id": _last_job_error_id,
        "last_job_error_at": _last_job_error_at,
        "event_error_count": _event_error_count,
        "job_error_count": _job_error_count,
    }


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


def touch_health() -> None:
    """Update the heartbeat file used by ``scripts/healthcheck.py``."""
    try:
        HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
        HEALTH_PATH.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        logging.getLogger("tramice.health").warning("Could not update health file")


def log_turn(
    *,
    user_id: str,
    channel_id: str,
    guild_id: str | None,
    trigger: str,
    duration_ms: float,
    model: str | None = None,
    tool_calls: int = 0,
    status: str = "ok",
) -> None:
    """Structured log for one agent turn (spec §11.2)."""
    _turn_log.info(
        "agent_turn",
        extra={
            "user_id": user_id,
            "channel_id": channel_id,
            "guild_id": guild_id,
            "trigger": trigger,
            "duration_ms": round(duration_ms, 1),
            "model": model,
            "tool_calls": tool_calls,
            "status": status,
        },
    )
    touch_health()


def log_job(*, job_id: str, duration_ms: float, status: str = "ok", **fields) -> None:
    """Structured log for a scheduled job completion."""
    extra = {
        "job_id": job_id,
        "duration_ms": round(duration_ms, 1),
        "status": status,
        **fields,
    }
    _job_log.info("scheduler_job", extra=extra)
    if status == "error":
        record_job_error(job_id)
    touch_health()


def audit(
    user_id: str,
    action: str,
    tool: str | None = None,
    args: dict | None = None,
    result: str = "ok",
) -> None:
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
