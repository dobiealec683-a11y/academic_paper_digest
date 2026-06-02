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

INSUFFICIENT_CONTEXT_MARKERS = (
    "couldn't find enough context",
    "could not find enough context",
    "not enough context",
    "try giving me more specific keywords",
)


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


def select_curated_paper(index: int, papers: list[dict[str, object]] = CURATED_FINANCE_PAPERS) -> tuple[int, dict[str, object]]:
    if not papers:
        raise ValueError("Curated paper queue is empty.")
    selected_index = index % len(papers)
    return selected_index, papers[selected_index]


def _run_notebooklm(topic: str, mode: str, source_urls: list[str] | None = None) -> list[Path]:
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
    for url in source_urls or []:
        if url and url not in sources:
            sources.append(url)
    bridge.batch_add_sources(notebook_id, sources)

    outputs = [(prompt, f"{slug}_{suffix}.md") for prompt, suffix in FINANCE_DAILY_PROMPTS]
    paths = []
    for prompt, filename in outputs:
        bridge.ask_notebook(notebook_id, prompt, filename)
        paths.append(config.EXPORTS_DIR / filename)
    return paths


def _validate_notebooklm_outputs(paths: list[Path]) -> None:
    failed_outputs = []
    for path in paths:
        if not path.exists():
            failed_outputs.append(f"{path.name}: missing output")
            continue
        text = path.read_text(encoding="utf-8").lower()
        if any(marker in text for marker in INSUFFICIENT_CONTEXT_MARKERS):
            failed_outputs.append(f"{path.name}: NotebookLM reported insufficient context")
    if failed_outputs:
        raise RuntimeError(
            "NotebookLM did not have enough paper text to produce a usable digest. "
            "No Telegram message was sent and the paper queue was not advanced. "
            "Failures: "
            + "; ".join(failed_outputs)
        )


def _source_urls_from_ranked(ranked: pd.DataFrame) -> list[str]:
    urls: list[str] = []
    for column in ("pdf_url", "landing_page_url", "oa_url"):
        if column not in ranked:
            continue
        for value in ranked[column].dropna().tolist():
            if isinstance(value, str) and value and value != "N/A" and value.startswith("http"):
                urls.append(value)
    return list(dict.fromkeys(urls))


def _source_urls_from_queued_paper(queued_paper: dict[str, object]) -> list[str]:
    values = queued_paper.get("source_urls", [])
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and value.startswith("http")]


def run_next_curated_paper(
    *,
    mode: str = config.NOTEBOOKLM_MODE,
    send_telegram: bool = True,
    state_path: Path = config.CURATED_STATE_FILE,
) -> dict[str, Any]:
    current_index = load_queue_index(state_path)
    selected_index, queued_paper = select_curated_paper(current_index)

    client = OpenAlexClient(email=config.OPENALEX_EMAIL)
    doi = str(queued_paper["doi"])
    paper = client.get_work_by_doi(doi)
    fallback_source_urls = _source_urls_from_queued_paper(queued_paper)
    if fallback_source_urls:
        paper["pdf_url"] = fallback_source_urls[0]
        paper["oa_url"] = fallback_source_urls[0]
    topic = str(paper.get("title") or queued_paper["title"])

    ranked = rank_papers([paper], topic)
    ranked_csv = config.OUTPUT_DIR / f"ranked_papers_{topic_slug(topic)}.csv"
    ranked.to_csv(ranked_csv, index=False)

    downloaded, failed = PDFCollector().collect_sources(topic, ranked)
    digest_sources = downloaded if not downloaded.empty else failed

    source_urls = list(dict.fromkeys([*fallback_source_urls, *_source_urls_from_ranked(ranked)]))
    notebooklm_outputs = _run_notebooklm(topic, mode, source_urls=source_urls)
    _validate_notebooklm_outputs(notebooklm_outputs)
    digest_path = DigestBuilder().build_digests(topic, digest_sources)
    attachments = send_digest_telegram(topic) if send_telegram else []

    next_index = (selected_index + 1) % len(CURATED_FINANCE_PAPERS)
    save_queue_index(next_index, state_path)

    result = {
        "paper_index": selected_index,
        "next_index": next_index,
        "title": topic,
        "doi": doi,
        "ranked_csv": str(ranked_csv),
        "digest_path": str(digest_path),
        "telegram_attachments": [str(path) for path in attachments],
    }
    RunHistory().append("curated_daily_paper", status="succeeded", topic=topic, details=result)
    logger.info("Completed curated daily paper", extra=log_context(**result))
    return result
