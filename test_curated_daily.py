from pathlib import Path

from curated_daily import load_queue_index, save_queue_index, select_curated_paper


def test_select_curated_paper_wraps_queue_index() -> None:
    papers = [{"title": "A", "doi": "10/a"}, {"title": "B", "doi": "10/b"}]

    index, paper = select_curated_paper(3, papers)

    assert index == 1
    assert paper == {"title": "B", "doi": "10/b"}


def test_queue_index_round_trips(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"

    save_queue_index(7, state_path)

    assert load_queue_index(state_path) == 7
