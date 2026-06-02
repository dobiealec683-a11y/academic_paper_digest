#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/alecdobie/Library/Application Support/AcademicResearchAssistant"
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"
export PATH="/Library/Frameworks/Python.framework/Versions/3.10/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
LOG_DIR="$PROJECT_DIR/outputs/logs"
STATE_DIR="$PROJECT_DIR/outputs/automation_state"
LOG_FILE="$LOG_DIR/daily_telegram_digest.log"
LOCK_DIR="$STATE_DIR/daily_digest.lock"
TODAY="$(date '+%Y-%m-%d')"
SUCCESS_MARKER="$STATE_DIR/daily_digest_success_$TODAY"
FAILURE_MARKER="$STATE_DIR/daily_digest_last_failure_$TODAY.log"

mkdir -p "$LOG_DIR" "$STATE_DIR"
cd "$PROJECT_DIR"

{
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Daily digest scheduler wake"

  if [[ -f "$SUCCESS_MARKER" ]]; then
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Success marker exists for $TODAY; skipping duplicate send"
    exit 0
  fi

  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Another digest run is already active; skipping"
    exit 0
  fi
  trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Starting curated daily Telegram digest attempt for $TODAY"
  if "$PYTHON_BIN" cli.py curated-daily --mode notebooklm_py; then
    touch "$SUCCESS_MARKER"
    rm -f "$FAILURE_MARKER"
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Finished curated daily Telegram digest successfully"
  else
    exit_code=$?
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Curated daily Telegram digest failed with exit code $exit_code"
    echo "Last failure: $(date -u '+%Y-%m-%dT%H:%M:%SZ') exit_code=$exit_code" > "$FAILURE_MARKER"
    echo "The paper queue advances only after a successful run, so the same paper will retry on the next scheduled wake."
    exit "$exit_code"
  fi
} >> "$LOG_FILE" 2>&1
