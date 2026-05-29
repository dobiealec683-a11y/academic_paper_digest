#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/alecdobie/Desktop/Learning/academic_research_assistant"
LOG_DIR="$PROJECT_DIR/outputs/logs"
LOG_FILE="$LOG_DIR/daily_telegram_digest.log"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

{
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Starting curated daily Telegram digest"
  /usr/bin/python3 cli.py curated-daily --mode notebooklm_py
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Finished curated daily Telegram digest"
} >> "$LOG_FILE" 2>&1
