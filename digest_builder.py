from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from config import DIGESTS_DIR, EXPORTS_DIR
from utils import log_context, topic_slug

logger = logging.getLogger(__name__)


class DigestBuilder:
    def __init__(self) -> None:
        self.digests_dir = DIGESTS_DIR
        self.exports_dir = EXPORTS_DIR

    def build_digests(self, topic: str, df_downloaded: pd.DataFrame) -> Path:
        """
        Builds the consolidated digests from downloaded paper data and NotebookLM exports.
        """
        if not topic.strip():
            raise ValueError("Topic cannot be empty when building digests.")

        slug = topic_slug(topic)
        self.digests_dir.mkdir(parents=True, exist_ok=True)
        
        # Load sources from exports if they exist
        extraction_path = self.exports_dir / f"{slug}_extraction.md"
        synthesis_path = self.exports_dir / f"{slug}_synthesis.md"
        digest_path = self.exports_dir / f"{slug}_digest.md"
        map_path = self.exports_dir / f"{slug}_map.md"

        # Read contents, fallback to mock if they don't exist
        extraction_content = self._read_file_or_default(extraction_path, "No per-paper extraction data available.")
        synthesis_content = self._read_file_or_default(synthesis_path, "No synthesis data available.")
        digest_content = self._read_file_or_default(digest_path, "No executive digest available.")
        map_content = self._read_file_or_default(map_path, "No research map available.")

        # 1. Write executive_brief.md
        with open(self.digests_dir / f"{slug}_executive_brief.md", "w", encoding="utf-8") as f:
            f.write(digest_content)

        # 2. Write research_map.md
        with open(self.digests_dir / f"{slug}_research_map.md", "w", encoding="utf-8") as f:
            f.write(map_content)

        # 3. Create literature_table.csv (Extract table from extraction markdown or fallback)
        df_lit = self._parse_markdown_table_to_df(extraction_content, df_downloaded)
        df_lit.to_csv(self.digests_dir / f"{slug}_literature_table.csv", index=False)

        # 4. Build and write daily_digest.md
        papers_added_str = ""
        if not df_downloaded.empty:
            for _, row in df_downloaded.head(5).iterrows():
                source_path = row.get("local_pdf_path") or row.get("local_metadata_path") or "N/A"
                papers_added_str += f"""### {row['title']}
- **Authors/Year:** {row['authors']} ({row['year']})
- **Source Package:** `{source_path}`
- **Source Link:** [Link]({row['pdf_url'] or '#'})
"""
        else:
            papers_added_str = "_No new papers were successfully downloaded. Using metadata URLs._\n"

        daily_digest = f"""# Daily Research Digest: {topic}

## Top Papers Added
{papers_added_str}

## NotebookLM Synthesis
{synthesis_content}

## Recommended Next Actions
- Read the top-scoring papers in the literature table.
- Add additional keywords to expand your search tomorrow.
- Consider exploring connected themes outlined in the research map.
"""
        
        digest_out_path = self.digests_dir / f"{slug}_daily_digest.md"
        with open(digest_out_path, "w", encoding="utf-8") as f:
            f.write(daily_digest)

        logger.info("Built digest package", extra=log_context(topic=topic, path=str(digest_out_path)))
        return digest_out_path

    def _read_file_or_default(self, path: Path, default_text: str) -> str:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return default_text

    def _parse_markdown_table_to_df(self, markdown_text: str, df_downloaded: pd.DataFrame) -> pd.DataFrame:
        """
        Parses simple markdown tables into pandas DataFrames.
        If table parsing fails, falls back to metadata list.
        """
        try:
            lines = [line.strip() for line in markdown_text.split("\n") if "|" in line]
            if len(lines) > 2:
                # Basic markdown table parser
                headers = [h.strip() for h in lines[0].split("|")[1:-1]]
                rows = []
                for line in lines[2:]:
                    # Skip delimiter row
                    if "---" in line or ":" in line:
                        continue
                    row = [r.strip() for r in line.split("|")[1:-1]]
                    if len(row) == len(headers):
                        rows.append(row)
                if rows:
                    return pd.DataFrame(rows, columns=headers)
        except (IndexError, ValueError) as exc:
            logger.warning("Failed to parse NotebookLM markdown table", extra=log_context(error=str(exc)))

        # Fallback DataFrame
        if not df_downloaded.empty:
            return df_downloaded[["title", "authors", "year", "pdf_url"]].copy()
        
        return pd.DataFrame(columns=["Title", "Authors", "Year", "Source"])
