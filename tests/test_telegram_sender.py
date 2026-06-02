from pathlib import Path

import pytest

from telegram_sender import (
    TelegramSettings,
    build_digest_notification,
    send_digest_telegram,
    validate_telegram_settings,
)


class DummyResponse:
    text = '{"ok": true}'

    def raise_for_status(self) -> None:
        return None


def test_validate_telegram_settings_reports_missing_configuration() -> None:
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        validate_telegram_settings(TelegramSettings(bot_token="", chat_id=""))


def test_build_digest_notification_is_short_and_file_oriented(tmp_path: Path) -> None:
    digest = tmp_path / "digest.md"
    table = tmp_path / "table.csv"

    message = build_digest_notification("test topic", [digest, table])

    assert message == (
        "Research digest ready: test topic\n\n"
        "Attached: 2 digest files.\n"
        "Open the daily digest first for the main summary."
    )


def test_build_digest_notification_mentions_audio_when_included(tmp_path: Path) -> None:
    digest = tmp_path / "digest.md"
    audio = tmp_path / "digest.m4a"

    message = build_digest_notification("test topic", [digest], [audio])

    assert message == (
        "Research digest ready: test topic\n\n"
        "Attached: 1 digest file.\n"
        "Open the daily digest first for the main summary.\n"
        "Audio readout: 1 audio file."
    )


def test_send_digest_telegram_posts_message_and_documents(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_post(url, data=None, files=None, timeout=None):
        calls.append({"url": url, "data": data, "files": files, "timeout": timeout})
        return DummyResponse()

    monkeypatch.setattr("telegram_sender.requests.post", fake_post)
    digest = tmp_path / "topic_daily_digest.md"
    table = tmp_path / "topic_literature_table.csv"
    digest.write_text("# Digest", encoding="utf-8")
    table.write_text("Title,Year\nPaper,2024\n", encoding="utf-8")

    sent = send_digest_telegram(
        "topic",
        settings=TelegramSettings(bot_token="token", chat_id="123"),
        attachments=[digest, table],
        include_audio=False,
    )

    assert sent == [digest, table]
    assert calls[0]["url"].endswith("/sendMessage")
    assert calls[0]["data"]["chat_id"] == "123"
    assert calls[0]["data"]["text"] == (
        "Research digest ready: topic\n\n"
        "Attached: 2 digest files.\n"
        "Open the daily digest first for the main summary."
    )
    assert calls[1]["url"].endswith("/sendDocument")
    assert calls[2]["url"].endswith("/sendDocument")


def test_send_digest_telegram_posts_audio_for_markdown_files(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_post(url, data=None, files=None, timeout=None):
        calls.append({"url": url, "data": data, "files": files, "timeout": timeout})
        return DummyResponse()

    digest = tmp_path / "topic_daily_digest.md"
    table = tmp_path / "topic_literature_table.csv"
    audio = tmp_path / "topic_daily_digest_readout.m4a"
    digest.write_text("# Digest", encoding="utf-8")
    table.write_text("Title,Year\nPaper,2024\n", encoding="utf-8")
    audio.write_bytes(b"audio")

    def fake_audio(topic: str, markdown_paths: list[Path]) -> list[Path]:
        assert topic == "topic"
        assert markdown_paths == [digest]
        return [audio]

    monkeypatch.setattr("telegram_sender.requests.post", fake_post)
    monkeypatch.setattr("telegram_sender.build_markdown_audio_files", fake_audio)

    sent = send_digest_telegram(
        "topic",
        settings=TelegramSettings(bot_token="token", chat_id="123"),
        attachments=[digest, table],
        include_audio=True,
    )

    assert sent == [digest, table, audio]
    assert calls[0]["data"]["text"].endswith("Audio readout: 1 audio file.")
    assert calls[1]["url"].endswith("/sendDocument")
    assert calls[2]["url"].endswith("/sendDocument")
    assert calls[3]["url"].endswith("/sendAudio")
    assert calls[3]["data"]["title"] == "topic_daily_digest_readout"
