"""Text-to-speech generation for digest markdown files."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

import config
from utils import log_context, topic_slug

logger = logging.getLogger(__name__)


class TextToSpeechError(RuntimeError):
    """Raised when configured text-to-speech generation cannot complete."""


def markdown_audio_paths(topic: str) -> list[Path]:
    slug = topic_slug(topic)
    return sorted(config.AUDIOS_DIR.glob(f"{slug}_*.m4a"))


def build_markdown_audio_files(
    topic: str,
    markdown_paths: list[Path],
    *,
    engine: str | None = None,
) -> list[Path]:
    """Create one audio readout per markdown file, preserving the source text."""
    selected_engine = engine or config.TTS_ENGINE
    if selected_engine == "disabled":
        logger.info("Telegram audio generation is disabled", extra=log_context(topic=topic))
        return []

    audio_paths: list[Path] = []
    for markdown_path in markdown_paths:
        if markdown_path.suffix.lower() != ".md" or not markdown_path.exists():
            continue
        audio_paths.append(_build_one_markdown_audio(markdown_path, selected_engine))
    return audio_paths


def _build_one_markdown_audio(markdown_path: Path, engine: str) -> Path:
    config.AUDIOS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = config.AUDIOS_DIR / f"{markdown_path.stem}_readout.m4a"
    if engine == "piper":
        return _build_with_piper(markdown_path, output_path)
    if engine == "say":
        return _build_with_say(markdown_path, output_path)
    if engine != "auto":
        raise TextToSpeechError(f"Unsupported TTS_ENGINE value: {engine}")

    try:
        return _build_with_piper(markdown_path, output_path)
    except TextToSpeechError as exc:
        logger.warning(
            "Piper TTS unavailable; falling back to macOS say",
            extra=log_context(path=str(markdown_path), error=str(exc)),
        )
        return _build_with_say(markdown_path, output_path)


def _build_with_piper(markdown_path: Path, output_path: Path) -> Path:
    piper_bin = shutil.which(config.PIPER_BIN) if not Path(config.PIPER_BIN).exists() else config.PIPER_BIN
    if not piper_bin:
        raise TextToSpeechError("Piper executable was not found. Set PIPER_BIN or install piper.")
    if not config.PIPER_MODEL_PATH:
        raise TextToSpeechError("PIPER_MODEL_PATH is not set.")
    model_path = Path(config.PIPER_MODEL_PATH).expanduser()
    if not model_path.exists():
        raise TextToSpeechError(f"Piper model does not exist: {model_path}")

    wav_path = output_path.with_suffix(".wav")
    text = markdown_path.read_text(encoding="utf-8")
    _run_tts_command(
        [str(piper_bin), "--model", str(model_path), "--output_file", str(wav_path)],
        input_text=text,
        failure_message="Piper failed to generate audio",
    )
    _convert_wav_to_m4a(wav_path, output_path)
    wav_path.unlink(missing_ok=True)
    logger.info("Built Piper audio readout", extra=log_context(source=str(markdown_path), audio=str(output_path)))
    return output_path


def _build_with_say(markdown_path: Path, output_path: Path) -> Path:
    say_bin = "/usr/bin/say"
    if not Path(say_bin).exists():
        raise TextToSpeechError("macOS say executable was not found.")
    _run_tts_command([say_bin, "-f", str(markdown_path), "-o", str(output_path)], failure_message="macOS say failed")
    logger.info("Built macOS say audio readout", extra=log_context(source=str(markdown_path), audio=str(output_path)))
    return output_path


def _convert_wav_to_m4a(wav_path: Path, output_path: Path) -> None:
    afconvert = "/usr/bin/afconvert"
    if not Path(afconvert).exists():
        raise TextToSpeechError("afconvert was not found; cannot convert Piper WAV output to M4A.")
    _run_tts_command(
        [afconvert, "-f", "m4af", "-d", "aac", str(wav_path), str(output_path)],
        failure_message="afconvert failed to convert Piper audio",
    )


def _run_tts_command(cmd: list[str], *, failure_message: str, input_text: str | None = None) -> None:
    try:
        subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise TextToSpeechError(f"{failure_message}{detail}") from exc
