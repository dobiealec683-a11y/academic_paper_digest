from pathlib import Path

import pandas as pd
import pytest

from curated_daily import (
    _source_urls_from_queued_paper,
    _source_urls_from_ranked,
    _validate_notebooklm_outputs,
    load_queue_index,
    save_queue_index,
    select_curated_paper,
)


def test_select_curated_paper_wraps_queue_index() -> None:
    papers = [{"title": "A", "doi": "10/a"}, {"title": "B", "doi": "10/b"}]

    index, paper = select_curated_paper(3, papers)

    assert index == 1
    assert paper == {"title": "B", "doi": "10/b"}


def test_queue_index_round_trips(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"

    save_queue_index(7, state_path)

    assert load_queue_index(state_path) == 7


def test_source_urls_from_ranked_collects_unique_urls() -> None:
    ranked = pd.DataFrame(
        [
            {
                "pdf_url": "https://example.com/paper.pdf",
                "landing_page_url": "https://example.com/article",
                "oa_url": "https://example.com/paper.pdf",
            }
        ]
    )

    assert _source_urls_from_ranked(ranked) == [
        "https://example.com/paper.pdf",
        "https://example.com/article",
    ]


def test_source_urls_from_queued_paper_accepts_manual_fallbacks() -> None:
    queued = {"title": "A", "doi": "10/a", "source_urls": ["https://example.com/a.pdf", "not-a-url"]}

    assert _source_urls_from_queued_paper(queued) == ["https://example.com/a.pdf"]


def test_validate_notebooklm_outputs_rejects_insufficient_context(tmp_path: Path) -> None:
    output = tmp_path / "synthesis.md"
    output.write_text("I'm sorry, but I couldn't find enough context in the document.", encoding="utf-8")

    with pytest.raises(RuntimeError, match="insufficient context"):
        _validate_notebooklm_outputs([output])
