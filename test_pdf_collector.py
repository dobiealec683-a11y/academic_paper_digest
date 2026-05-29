import pandas as pd

from pdf_collector import build_metadata_markdown


def test_build_metadata_markdown_contains_notebooklm_companion_fields() -> None:
    row = pd.Series(
        {
            "title": "A Useful Paper",
            "openalex_id": "W1",
            "doi": "10.1/example",
            "authors": "Ada Lovelace",
            "year": 2024,
            "citations": 12,
            "journal_source": "Test Journal",
            "pdf_url": "https://example.org/paper.pdf",
            "landing_page_url": "https://example.org/article",
            "reason_selected": "Direct Open-Access PDF available",
            "abstract": "This is the abstract.",
            "total_score": 88.5,
            "relevance_score": 40.0,
            "citation_score": 10.0,
            "recency_score": 14.0,
            "oa_score": 10.0,
            "pdf_score": 10.0,
            "penalty": 0.0,
        }
    )

    markdown = build_metadata_markdown(row, pdf_downloaded=True)

    assert markdown.startswith("# A Useful Paper")
    assert "**OpenAlex ID:** W1" in markdown
    assert "## Abstract\nThis is the abstract." in markdown
    assert "- PDF Available: Yes" in markdown
