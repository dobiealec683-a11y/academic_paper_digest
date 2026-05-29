"""Telegram delivery for generated research digests."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import requests

import config
from utils import log_context, topic_slug

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class TelegramSettings:
    bot_token: str
    chat_id: str


def load_telegram_settings() -> TelegramSettings:
    return TelegramSettings(
        bot_token=config.TELEGRAM_BOT_TOKEN,
        chat_id=config.TELEGRAM_CHAT_ID,
    )


def validate_telegram_settings(settings: TelegramSettings) -> None:
    missing = [
        name
        for name, value in {
            "TELEGRAM_BOT_TOKEN": settings.bot_token,
            "TELEGRAM_CHAT_ID": settings.chat_id,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(
            "Telegram delivery is not configured. Set these values in .env: "
            + ", ".join(missing)
            + ". Create a free bot with BotFather, send it one message, then get your chat id."
        )


def build_digest_notification(topic: str, attachments: list[Path]) -> str:
    file_count = len(attachments)
    file_label = "file" if file_count == 1 else "files"
    return (
        f"Research digest ready: {topic}\n\n"
        f"Attached: {file_count} digest {file_label}.\n"
        "Open the daily digest first for the main summary."
    )


def digest_attachment_paths(topic: str) -> list[Path]:
    slug = topic_slug(topic)
    candidates = [
        config.DIGESTS_DIR / f"{slug}_daily_digest.md",
        config.DIGESTS_DIR / f"{slug}_executive_brief.md",
        config.DIGESTS_DIR / f"{slug}_research_map.md",
        config.DIGESTS_DIR / f"{slug}_literature_table.csv",
    ]
    return [path for path in candidates if path.exists()]


def _telegram_url(settings: TelegramSettings, method: str) -> str:
    return f"https://api.telegram.org/bot{settings.bot_token}/{method}"


def _raise_for_telegram_error(response: requests.Response, action: str) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text[:500]
        raise RuntimeError(f"Telegram {action} failed: {detail}") from exc


def send_digest_telegram(
    topic: str,
    *,
    settings: TelegramSettings | None = None,
    attachments: list[Path] | None = None,
) -> list[Path]:
    telegram_settings = settings or load_telegram_settings()
    validate_telegram_settings(telegram_settings)

    attachment_paths = attachments if attachments is not None else digest_attachment_paths(topic)
    message_response = requests.post(
        _telegram_url(telegram_settings, "sendMessage"),
        data={
            "chat_id": telegram_settings.chat_id,
            "text": build_digest_notification(topic, attachment_paths),
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    _raise_for_telegram_error(message_response, "message send")

    for path in attachment_paths:
        with path.open("rb") as file:
            document_response = requests.post(
                _telegram_url(telegram_settings, "sendDocument"),
                data={"chat_id": telegram_settings.chat_id},
                files={"document": (path.name, file)},
                timeout=60,
            )
        _raise_for_telegram_error(document_response, f"document send for {path.name}")

    logger.info(
        "Sent digest to Telegram",
        extra=log_context(topic=topic, attachments=[str(path) for path in attachment_paths]),
    )
    return attachment_paths
