from __future__ import annotations

import logging

import requests
import pandas as pd
from config import PDFS_DIR, METADATA_DIR
from utils import log_context, sanitize_filename, topic_slug

logger = logging.getLogger(__name__)


def build_metadata_markdown(row: pd.Series, *, pdf_downloaded: bool) -> str:
    """Build NotebookLM companion metadata markdown for a ranked paper."""

    return f"""# {row['title']}

**OpenAlex ID:** {row['openalex_id']}
**DOI:** {row['doi']}
**Authors:** {row['authors']}
**Year:** {row['year']}
**Citation Count:** {row['citations']}
**Source:** {row['journal_source']}
**PDF URL:** {row['pdf_url'] or 'N/A'}
**Landing Page:** {row['landing_page_url'] or 'N/A'}
**Reason Selected:** {row['reason_selected']}

## Abstract
{row['abstract']}

## Why this paper was included
This paper was included because it scored well (Total Score: {row['total_score']}/100) under our multi-criteria ranking algorithm.
Key factors:
- Relevance Score: {row['relevance_score']}/40 (Keyword overlap match)
- Citation Score: {row['citation_score']}/25
- Recency Score: {row['recency_score']}/15
- Open Access: {'Yes' if row['oa_score'] > 0 else 'No'} (OA Score: {row['oa_score']}/10)
- PDF Available: {'Yes' if pdf_downloaded else 'No'} (PDF Score: {row['pdf_score']}/10)
- Penalties Applied: {row['penalty']}
"""

class PDFCollector:
    def __init__(self, timeout_seconds: int = 15) -> None:
        self.pdfs_dir = PDFS_DIR
        self.metadata_dir = METADATA_DIR
        self.timeout_seconds = timeout_seconds

    def collect_sources(self, topic: str, df_ranked: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Download PDFs when available and build metadata companion files for all ranked papers.
        """
        if not topic.strip():
            raise ValueError("Topic cannot be empty when collecting PDFs and metadata.")
        if df_ranked.empty:
            raise ValueError("No ranked papers were provided to the PDF collector.")

        slug = topic_slug(topic)
        topic_pdf_dir = self.pdfs_dir / slug
        topic_meta_dir = self.metadata_dir / slug
        
        topic_pdf_dir.mkdir(parents=True, exist_ok=True)
        topic_meta_dir.mkdir(parents=True, exist_ok=True)

        downloaded_records: list[dict[str, object]] = []
        failed_records: list[dict[str, object]] = []

        logger.info("Collecting source package", extra=log_context(topic=topic, papers=len(df_ranked)))
        for _, row in df_ranked.iterrows():
            title = row["title"]
            pdf_url = row.get("pdf_url")
            safe_title = sanitize_filename(title)
            
            pdf_filename = f"{safe_title}.pdf"
            pdf_filepath = topic_pdf_dir / pdf_filename
            meta_filename = f"{safe_title}_metadata.md"
            meta_filepath = topic_meta_dir / meta_filename

            download_success = False
            error_msg = ""
            
            if pdf_url:
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    response = requests.get(
                        pdf_url,
                        headers=headers,
                        timeout=self.timeout_seconds,
                        stream=True,
                    )
                    if response.status_code == 200:
                        with open(pdf_filepath, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        download_success = True
                    else:
                        error_msg = f"HTTP {response.status_code}"
                except requests.RequestException as exc:
                    error_msg = f"PDF download failed: {exc}"
            else:
                error_msg = "No direct PDF URL available"

            record = {
                "rank": row["rank"],
                "title": title,
                "authors": row["authors"],
                "year": row["year"],
                "pdf_url": pdf_url or "",
                "local_pdf_path": str(pdf_filepath) if download_success else "",
                "local_metadata_path": str(meta_filepath),
                "error": error_msg
            }
            
            if download_success:
                downloaded_records.append(record)
            else:
                failed_records.append(record)

            with open(meta_filepath, "w", encoding="utf-8") as f:
                f.write(build_metadata_markdown(row, pdf_downloaded=download_success))

        # Write reports
        df_downloaded = pd.DataFrame(downloaded_records)
        df_failed = pd.DataFrame(failed_records)

        df_downloaded.to_csv(topic_pdf_dir / "downloaded_papers.csv", index=False)
        df_failed.to_csv(topic_pdf_dir / "failed_downloads.csv", index=False)

        logger.info(
            "Source package collected",
            extra=log_context(topic=topic, downloaded=len(df_downloaded), failed=len(df_failed)),
        )
        return df_downloaded, df_failed
