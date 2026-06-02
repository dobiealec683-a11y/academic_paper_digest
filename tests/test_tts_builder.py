from pathlib import Path

import tts_builder
from tts_builder import build_markdown_audio_files


def test_build_markdown_audio_files_only_reads_markdown(tmp_path: Path, monkeypatch) -> None:
    markdown = tmp_path / "paper_daily_digest.md"
    csv = tmp_path / "paper_literature_table.csv"
    audio = tmp_path / "paper_daily_digest_readout.m4a"
    markdown.write_text("# Digest\nExact markdown text.", encoding="utf-8")
    csv.write_text("title,year\nPaper,2024\n", encoding="utf-8")

    calls = []

    def fake_build_one(path: Path, engine: str) -> Path:
        calls.append((path, engine))
        return audio

    monkeypatch.setattr(tts_builder, "_build_one_markdown_audio", fake_build_one)

    assert build_markdown_audio_files("paper", [markdown, csv], engine="say") == [audio]
    assert calls == [(markdown, "say")]
