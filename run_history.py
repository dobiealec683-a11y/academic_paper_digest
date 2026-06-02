"""Append-only run history for CLI and dashboard operations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import RUN_HISTORY_FILE


class RunHistory:
    """Write one JSON object per pipeline event."""

    def __init__(self, path: Path = RUN_HISTORY_FILE) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        event: str,
        *,
        status: str,
        topic: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "status": status,
            "topic": topic,
            "details": details or {},
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
