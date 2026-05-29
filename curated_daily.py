"""Run one paper from the curated finance queue each day."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

import config
from curated_papers import CURATED_FINANCE_PAPERS
from digest_builder import DigestBuilder
from notebooklm_bridge import NotebookLMBridge
from openalex_client import OpenAlexClient
from paper_ranker import rank_papers
from pdf_collector import PDFCollector
from prompts import FINANCE_DAILY_PROMPTS
from run_history import RunHistory
from telegram_sender import send_digest_telegram
from utils import log_context, topic_slug

logger = logging.getLogger(__name__)


def load_queue_index(path: Path = config.CURATED_STATE_FILE) -> int:
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return int(data.get("next_index", 0))
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Curated paper state is invalid; restarting at first paper", extra=log_context(path=str(path)))
        return 0


def save_queue_index(index: int, path: Path = config.CURATED_STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"next_index": index}, indent=2), encoding="utf-8")


def select_curated_paper(index: int, papers: list[dict[str, str]] = CURATED_FINANCE_PAPERS) -> tuple[int, dict[str, str]]:
    if not papers:
        raise ValueError("Curated paper queue is empty.")
    selected_index = index % len(papers)
    return selected_index, papers[selected_index]


def _run_notebooklm(topic: str, mode: str) -> list[Path]:
    slug = topic_slug(topic)
    bridge = NotebookLMBridge(mode=mode)
    notebook_id = bridge.create_notebook(topic)

    sources: list[Path] = []
    metadata_dir = config.METADATA_DIR / slug
    pdf_dir = config.PDFS_DIR / slug
    if metadata_dir.exists():
        sources.extend(metadata_dir.glob("*.md"))
    if pdf_dir.exists():
        sources.extend(pdf_dir.glob("*.pdf"))
    bridge.batch_add_sources(notebook_id, sources)

    outputs = [(prompt, f"{slug}_{suffix}.md") for prompt, suffix in FINANCE_DAILY_PROMPTS]
    paths = []
    for prompt, filename in outputs:
        bridge.ask_notebook(notebook_id, prompt, filename)
        paths.append(config.EXPORTS_DIR / filename)
    return paths


def run_next_curated_paper(
    *,
    mode: str = config.NOTEBOOKLM_MODE,
    send_telegram: bool = True,
    state_path: Path = config.CURATED_STATE_FILE,
) -> dict[str, Any]:
    current_index = load_queue_index(state_path)
    selected_index, queued_paper = select_curated_paper(current_index)

    client = OpenAlexClient(email=config.OPENALEX_EMAIL)
    paper = client.get_work_by_doi(queued_paper["doi"])
    topic = paper.get("title") or queued_paper["title"]

    ranked = rank_papers([paper], topic)
    ranked_csv = config.OUTPUT_DIR / f"ranked_papers_{topic_slug(topic)}.csv"
    ranked.to_csv(ranked_csv, index=False)

    downloaded, failed = PDFCollector().collect_sources(topic, ranked)
    digest_sources = downloaded if not downloaded.empty else failed

    _run_notebooklm(topic, mode)
    digest_path = DigestBuilder().build_digests(topic, digest_sources)
    attachments = send_digest_telegram(topic) if send_telegram else []

    next_index = (selected_index + 1) % len(CURATED_FINANCE_PAPERS)
    save_queue_index(next_index, state_path)

    result = {
        "paper_index": selected_index,
        "next_index": next_index,
        "title": topic,
        "doi": queued_paper["doi"],
        "ranked_csv": str(ranked_csv),
        "digest_path": str(digest_path),
        "telegram_attachments": [str(path) for path in attachments],
    }
    RunHistory().append("curated_daily_paper", status="succeeded", topic=topic, details=result)
    logger.info("Completed curated daily paper", extra=log_context(**result))
    return result
