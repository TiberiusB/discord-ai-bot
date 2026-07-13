#!/usr/bin/env python3
"""Container/process health probe for Tramice721.

Exits 0 when ``data/.health`` was updated recently (bot heartbeat).
Used by Docker HEALTHCHECK and optional external monitors.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEALTH = ROOT / "data" / ".health"
MAX_AGE_SEC = 300  # 5 minutes


def main() -> int:
    if not HEALTH.exists():
        print("health: missing heartbeat file", file=sys.stderr)
        return 1
    try:
        age = time.time() - float(HEALTH.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        print("health: unreadable heartbeat file", file=sys.stderr)
        return 1
    if age > MAX_AGE_SEC:
        print(f"health: stale heartbeat ({age:.0f}s old)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
