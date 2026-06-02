from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Workspace paths
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
METADATA_DIR = OUTPUT_DIR / "metadata"
PDFS_DIR = OUTPUT_DIR / "pdfs"
EXPORTS_DIR = OUTPUT_DIR / "notebooklm_exports"
DIGESTS_DIR = OUTPUT_DIR / "digests"
AUDIOS_DIR = OUTPUT_DIR / "audio"
LOGS_DIR = OUTPUT_DIR / "logs"
RUN_HISTORY_FILE = OUTPUT_DIR / "run_history.jsonl"
CURATED_STATE_FILE = OUTPUT_DIR / "curated_paper_state.json"

# Ensure all directories exist
for folder in [METADATA_DIR, PDFS_DIR, EXPORTS_DIR, DIGESTS_DIR, AUDIOS_DIR, LOGS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Environment variables with defaults
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "example@example.com")
NOTEBOOKLM_MODE = os.getenv("NOTEBOOKLM_MODE", "mock")  # Options: mock, notebooklm_py, enterprise
NOTEBOOKLM_STORAGE_STATE_PATH = os.getenv("NOTEBOOKLM_STORAGE_STATE_PATH", "")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
NOTEBOOKLM_LOCATION = os.getenv("NOTEBOOKLM_LOCATION", "us-central1")
NOTEBOOKLM_ENTERPRISE_ENDPOINT = os.getenv("NOTEBOOKLM_ENTERPRISE_ENDPOINT", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TTS_ENGINE = os.getenv("TTS_ENGINE", "auto")  # Options: auto, piper, say, disabled
PIPER_BIN = os.getenv("PIPER_BIN", "piper")
PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "")
ENABLE_TELEGRAM_AUDIO = os.getenv("ENABLE_TELEGRAM_AUDIO", "true").lower() in {"1", "true", "yes", "on"}
