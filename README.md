# Academic Research Assistant

Productionized research pipeline for discovering papers, collecting source files, routing reading and synthesis through NotebookLM, and publishing dashboard-ready digests.

## Architecture

```text
OpenAlex discovery
  -> paper scoring
  -> PDF collector ingestion
  -> NotebookLM paper reading and synthesis
  -> digest/dashboard output layer
```

NotebookLM remains the synthesis layer. The local `mock` mode is for development and tests; `notebooklm_py` delegates source upload and prompts to the local NotebookLM CLI.

## Fresh Setup

Run these commands from the repository root:

```bash
cd /Users/alecdobie/Desktop/Learning/academic_research_assistant
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
OPENALEX_EMAIL=your.email@example.com
NOTEBOOKLM_MODE=mock
NOTEBOOKLM_STORAGE_STATE_PATH=
GOOGLE_CLOUD_PROJECT=
NOTEBOOKLM_LOCATION=us-central1
NOTEBOOKLM_ENTERPRISE_ENDPOINT=
LOG_LEVEL=INFO
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Use a real email for `OPENALEX_EMAIL`; OpenAlex recommends mailto identification for polite API usage.

## Run the Dashboard

```bash
source .venv/bin/activate
streamlit run main.py
```

The dashboard writes outputs under `outputs/`:

```text
outputs/cache/               OpenAlex raw and cleaned discovery results
outputs/pdfs/                downloaded PDFs and download reports
outputs/metadata/            companion markdown metadata for NotebookLM
outputs/notebooklm_exports/  NotebookLM prompt outputs
outputs/digests/             daily digest, executive brief, research map, table
outputs/logs/pipeline.log    structured JSON logs
outputs/run_history.jsonl    append-only run history
```

## Run the CLI

Full local dry run with mock NotebookLM synthesis:

```bash
source .venv/bin/activate
python cli.py run "corporate governance" --start-year 2020 --max-results 10 --open-access-only --mode mock
```

Run each phase separately:

```bash
python cli.py discover "corporate governance" --start-year 2020 --max-results 10
python cli.py collect "corporate governance" --ranked-csv outputs/ranked_papers_corporate_governance.csv
python cli.py synthesize "corporate governance" --mode mock
python cli.py digest "corporate governance" --downloaded-csv outputs/pdfs/corporate_governance/downloaded_papers.csv
```

Send existing digest files to Telegram:

```bash
python cli.py telegram "corporate governance"
```

Or send to Telegram as part of digest generation/full pipeline:

```bash
python cli.py digest "corporate governance" --telegram
python cli.py run "corporate governance" --start-year 2020 --max-results 10 --mode mock --telegram
```

Run the next paper from the curated DOI queue:

```bash
python cli.py curated-daily --mode notebooklm_py
```

The curated queue advances only after a successful run. Queue state is stored in:

```text
outputs/curated_paper_state.json
```

## Daily Local Automation

On macOS, install the local `launchd` job to run one paper from the curated DOI queue every day at 9:00 AM and send the digest to Telegram.

The job has hardcoded fail-safes:

- It wakes hourly from 9:00 AM through 8:00 PM.
- It sends at most once per day by writing a daily success marker.
- It uses a lock directory so overlapping runs cannot double-send.
- If OpenAlex, NotebookLM, PDF collection, or Telegram fails, it does not advance the paper queue.
- Failed runs retry on the next hourly wake.

```bash
chmod +x scripts/run_daily_telegram_digest.sh
chmod +x scripts/install_daily_digest_launchd.sh
scripts/install_daily_digest_launchd.sh
```

Run it immediately for a test:

```bash
launchctl kickstart -k gui/$(id -u)/com.alecdobie.academic-research-digest
```

Logs are written to:

```text
~/Library/Application Support/AcademicResearchAssistant/outputs/logs/daily_telegram_digest.log
~/Library/Application Support/AcademicResearchAssistant/outputs/logs/launchd_daily_digest.out.log
~/Library/Application Support/AcademicResearchAssistant/outputs/logs/launchd_daily_digest.err.log
~/Library/Application Support/AcademicResearchAssistant/outputs/automation_state/
```

Uninstall it:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.alecdobie.academic-research-digest.plist
rm ~/Library/LaunchAgents/com.alecdobie.academic-research-digest.plist
```

### Telegram Setup

Telegram delivery is free.

1. In Telegram, message `@BotFather`.
2. Run `/newbot` and follow the prompts.
3. Copy the bot token into `.env` as `TELEGRAM_BOT_TOKEN`.
4. Send any message to your new bot from your Telegram account.
5. Visit this URL in a browser, replacing `<TOKEN>`:

```text
https://api.telegram.org/bot<TOKEN>/getUpdates
```

6. Find `"chat":{"id":...}` in the response and copy that number into `.env` as `TELEGRAM_CHAT_ID`.

### Telegram Audio Readouts

Telegram delivery can also send free text-to-speech readouts of the generated markdown digest files. The audio feature reads each `.md` attachment word for word and ignores the `.csv` literature table.

By default, `TTS_ENGINE=auto` tries Piper first and falls back to the built-in macOS `say` command. The fallback is free and requires no setup.

To use free local Piper voices, install Piper and point the app at a downloaded voice model:

```bash
python3 -m pip install piper-tts
```

Then set:

```bash
ENABLE_TELEGRAM_AUDIO=true
TTS_ENGINE=auto
PIPER_BIN=piper
PIPER_MODEL_PATH=/absolute/path/to/your/piper-voice.onnx
```

To force macOS audio only:

```bash
TTS_ENGINE=say
```

To turn audio off:

```bash
ENABLE_TELEGRAM_AUDIO=false
```

For NotebookLM CLI mode, install and authenticate the external CLI first, then run:

```bash
notebooklm login
python cli.py synthesize "corporate governance" --mode notebooklm_py
```

`enterprise` mode intentionally raises a clear error until a concrete NotebookLM Enterprise client is wired in.

## Tests

```bash
source .venv/bin/activate
pytest
```

Current tests cover:

- OpenAlex abstract reconstruction
- OpenAlex work parsing
- PDF URL extraction
- paper scoring and ranking
- metadata markdown generation
- digest generation from NotebookLM exports

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `OPENALEX_EMAIL` | Email sent to OpenAlex in `mailto` | `example@example.com` |
| `NOTEBOOKLM_MODE` | `mock`, `notebooklm_py`, or `enterprise` | `mock` |
| `NOTEBOOKLM_STORAGE_STATE_PATH` | Reserved for browser/session integrations | empty |
| `GOOGLE_CLOUD_PROJECT` | Reserved for Enterprise mode | empty |
| `NOTEBOOKLM_LOCATION` | Reserved for Enterprise mode | `us-central1` |
| `NOTEBOOKLM_ENTERPRISE_ENDPOINT` | Reserved for Enterprise mode | empty |
| `LOG_LEVEL` | Python logging level | `INFO` |
| `TELEGRAM_BOT_TOKEN` | Free Telegram bot token from BotFather | empty |
| `TELEGRAM_CHAT_ID` | Your Telegram chat id for bot delivery | empty |
| `ENABLE_TELEGRAM_AUDIO` | Send TTS readouts of markdown digest files to Telegram | `true` |
| `TTS_ENGINE` | `auto`, `piper`, `say`, or `disabled` | `auto` |
| `PIPER_BIN` | Piper executable path/name | `piper` |
| `PIPER_MODEL_PATH` | Piper `.onnx` voice model path | empty |

## Notes

- OpenAlex metadata can be incomplete; missing abstracts and DOI values are penalized during scoring.
- PDF collection only downloads direct open-access PDF URLs. Metadata markdown is generated for every ranked paper so NotebookLM still receives a structured companion source.
- NotebookLM source limits depend on account and product tier.
- Telegram delivery sends a preview message plus the digest files as attachments. When audio is enabled, it also sends one audio readout per markdown digest file.
