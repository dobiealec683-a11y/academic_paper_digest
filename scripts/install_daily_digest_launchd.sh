#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/alecdobie/Desktop/Learning/academic_research_assistant"
RUNTIME_DIR="/Users/alecdobie/Library/Application Support/AcademicResearchAssistant"
LAUNCH_AGENT_DIR="/Users/alecdobie/Library/LaunchAgents"
LABEL="com.alecdobie.academic-research-digest"

mkdir -p "$RUNTIME_DIR" "$LAUNCH_AGENT_DIR"
mkdir -p "$RUNTIME_DIR/outputs"
cp "$PROJECT_DIR"/*.py "$RUNTIME_DIR/"
cp "$PROJECT_DIR/.env" "$RUNTIME_DIR/.env"
cp "$PROJECT_DIR/requirements.txt" "$RUNTIME_DIR/requirements.txt"
if [[ -f "$PROJECT_DIR/outputs/curated_paper_state.json" ]]; then
  mkdir -p "$RUNTIME_DIR/outputs"
  cp "$PROJECT_DIR/outputs/curated_paper_state.json" "$RUNTIME_DIR/outputs/curated_paper_state.json"
fi
cp "$PROJECT_DIR/scripts/run_daily_telegram_digest.sh" "$RUNTIME_DIR/run_daily_telegram_digest.sh"
chmod +x "$RUNTIME_DIR/run_daily_telegram_digest.sh"
cp "$PROJECT_DIR/launchd/$LABEL.plist" "$LAUNCH_AGENT_DIR/$LABEL.plist"

launchctl bootout "gui/$(id -u)" "$LAUNCH_AGENT_DIR/$LABEL.plist" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENT_DIR/$LABEL.plist"
launchctl enable "gui/$(id -u)/$LABEL"

echo "Installed $LABEL"
