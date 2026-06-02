"""Command line interface for the academic research assistant pipeline."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

import config
from curated_daily import run_next_curated_paper
from digest_builder import DigestBuilder
from notebooklm_bridge import NotebookLMBridge
from openalex_client import OpenAlexClient
from paper_ranker import rank_papers
from pdf_collector import PDFCollector
from prompts import (
    PROMPT_CROSS_PAPER_SYNTHESIS,
    PROMPT_EXECUTIVE_DIGEST,
    PROMPT_PER_PAPER_EXTRACTION,
    PROMPT_RESEARCH_MAP,
)
from run_history import RunHistory
from telegram_sender import send_digest_telegram
from utils import configure_logging, log_context, topic_slug

logger = logging.getLogger(__name__)


def discover(args: argparse.Namespace) -> Path:
    client = OpenAlexClient(email=args.email or config.OPENALEX_EMAIL)
    papers = client.search_works(
        query=args.topic,
        start_year=args.start_year,
        end_year=args.end_year,
        max_results=args.max_results,
        open_access_only=args.open_access_only,
        paper_type=args.paper_type,
        sort_by=args.sort_by,
    )
    ranked = rank_papers(papers, args.topic)
    output_path = config.OUTPUT_DIR / f"ranked_papers_{topic_slug(args.topic)}.csv"
    ranked.to_csv(output_path, index=False)
    logger.info("Wrote ranked papers", extra=log_context(path=str(output_path), rows=len(ranked)))
    return output_path


def collect(args: argparse.Namespace) -> tuple[Path, Path]:
    ranked = pd.read_csv(args.ranked_csv)
    downloaded, failed = PDFCollector().collect_sources(args.topic, ranked)
    slug = topic_slug(args.topic)
    pdf_dir = config.PDFS_DIR / slug
    return pdf_dir / "downloaded_papers.csv", pdf_dir / "failed_downloads.csv"


def synthesize(args: argparse.Namespace) -> list[Path]:
    slug = topic_slug(args.topic)
    bridge = NotebookLMBridge(mode=args.mode or config.NOTEBOOKLM_MODE)
    notebook_id = bridge.create_notebook(args.topic)

    sources: list[Path] = []
    metadata_dir = config.METADATA_DIR / slug
    pdf_dir = config.PDFS_DIR / slug
    if metadata_dir.exists():
        sources.extend(metadata_dir.glob("*.md"))
    if pdf_dir.exists():
        sources.extend(pdf_dir.glob("*.pdf"))
    bridge.batch_add_sources(notebook_id, sources)

    outputs = [
        (PROMPT_PER_PAPER_EXTRACTION, f"{slug}_extraction.md"),
        (PROMPT_CROSS_PAPER_SYNTHESIS, f"{slug}_synthesis.md"),
        (PROMPT_EXECUTIVE_DIGEST, f"{slug}_digest.md"),
        (PROMPT_RESEARCH_MAP, f"{slug}_map.md"),
    ]
    paths = []
    for prompt, filename in outputs:
        bridge.ask_notebook(notebook_id, prompt, filename)
        paths.append(config.EXPORTS_DIR / filename)
    return paths


def build_digest(args: argparse.Namespace) -> Path:
    if args.downloaded_csv and Path(args.downloaded_csv).exists():
        downloaded = pd.read_csv(args.downloaded_csv)
    else:
        downloaded = pd.DataFrame()
    digest_path = DigestBuilder().build_digests(args.topic, downloaded)
    if getattr(args, "telegram", False):
        send_digest_telegram(args.topic)
    return digest_path


def telegram_digest(args: argparse.Namespace) -> list[Path]:
    return send_digest_telegram(args.topic)


def run_curated_daily(args: argparse.Namespace) -> dict[str, object]:
    return run_next_curated_paper(mode=args.mode, send_telegram=not args.no_telegram)


def run_pipeline(args: argparse.Namespace) -> Path:
    ranked_csv = discover(args)
    args.ranked_csv = ranked_csv
    downloaded_csv, _ = collect(args)
    synthesize(args)
    args.downloaded_csv = downloaded_csv
    return build_digest(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="academic-research-assistant",
        description="OpenAlex discovery, PDF ingestion, NotebookLM synthesis, and digest generation.",
    )
    parser.add_argument("--log-level", default=config.LOG_LEVEL, help="Logging level, for example INFO or DEBUG.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_discovery_args(command: argparse.ArgumentParser) -> None:
        command.add_argument("topic", help="Research topic or OpenAlex query.")
        command.add_argument("--email", default=config.OPENALEX_EMAIL, help="OpenAlex mailto email.")
        command.add_argument("--start-year", type=int, default=None)
        command.add_argument("--end-year", type=int, default=None)
        command.add_argument("--max-results", type=int, default=20)
        command.add_argument("--open-access-only", action="store_true")
        command.add_argument("--paper-type", default=None)
        command.add_argument("--sort-by", default="cited_by_count:desc")

    discover_parser = subparsers.add_parser("discover", help="Search OpenAlex and rank papers.")
    add_discovery_args(discover_parser)
    discover_parser.set_defaults(func=discover)

    collect_parser = subparsers.add_parser("collect", help="Download PDFs and generate metadata markdown.")
    collect_parser.add_argument("topic")
    collect_parser.add_argument("--ranked-csv", required=True, type=Path)
    collect_parser.set_defaults(func=collect)

    synth_parser = subparsers.add_parser("synthesize", help="Upload sources and run NotebookLM prompts.")
    synth_parser.add_argument("topic")
    synth_parser.add_argument("--mode", default=config.NOTEBOOKLM_MODE, choices=["mock", "notebooklm_py", "enterprise"])
    synth_parser.set_defaults(func=synthesize)

    digest_parser = subparsers.add_parser("digest", help="Build dashboard digest files from NotebookLM exports.")
    digest_parser.add_argument("topic")
    digest_parser.add_argument("--downloaded-csv", default=None)
    digest_parser.add_argument("--telegram", action="store_true", help="Send generated digest files to Telegram.")
    digest_parser.set_defaults(func=build_digest)

    telegram_parser = subparsers.add_parser("telegram", help="Send existing digest files to Telegram.")
    telegram_parser.add_argument("topic")
    telegram_parser.set_defaults(func=telegram_digest)

    curated_parser = subparsers.add_parser("curated-daily", help="Run the next paper from the curated DOI queue.")
    curated_parser.add_argument("--mode", default=config.NOTEBOOKLM_MODE, choices=["mock", "notebooklm_py", "enterprise"])
    curated_parser.add_argument("--no-telegram", action="store_true", help="Build the digest without sending it to Telegram.")
    curated_parser.set_defaults(func=run_curated_daily)

    run_parser = subparsers.add_parser("run", help="Run discovery, ingestion, NotebookLM synthesis, and digest generation.")
    add_discovery_args(run_parser)
    run_parser.add_argument("--mode", default=config.NOTEBOOKLM_MODE, choices=["mock", "notebooklm_py", "enterprise"])
    run_parser.add_argument("--telegram", action="store_true", help="Send generated digest files to Telegram.")
    run_parser.set_defaults(func=run_pipeline)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level, config.LOGS_DIR / "pipeline.log")
    history = RunHistory()
    try:
        result = args.func(args)
    except Exception as exc:
        history.append(args.command, status="failed", topic=getattr(args, "topic", None), details={"error": str(exc)})
        logger.exception("Command failed", extra=log_context(command=args.command))
        print(f"Error: {exc}")
        return 1

    history.append(args.command, status="succeeded", topic=getattr(args, "topic", None), details={"result": str(result)})
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
