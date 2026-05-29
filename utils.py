"""Shared production helpers for the research pipeline."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    """Minimal structured formatter for console/file logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key.startswith("_") and key != "_context":
                continue
            if key == "_context" and isinstance(value, dict):
                payload.update(value)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Configure root logging once with structured JSON output."""

    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level.upper())
        return

    root.setLevel(level.upper())
    formatter = JsonFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def log_context(**kwargs: Any) -> dict[str, dict[str, Any]]:
    """Attach structured fields to a log record using logging's extra API."""

    return {"_context": kwargs}


def sanitize_filename(name: str, max_len: int = 60) -> str:
    """Sanitize a string for stable filenames."""

    sanitized = re.sub(r"[^\w\s-]", "", name or "")
    sanitized = re.sub(r"\s+", "_", sanitized.strip())
    return (sanitized[:max_len] or "untitled")


def topic_slug(topic: str) -> str:
    """Return a filesystem-safe topic slug."""

    return sanitize_filename(topic).lower()
