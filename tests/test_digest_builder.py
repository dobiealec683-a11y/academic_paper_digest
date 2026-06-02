import pandas as pd

import digest_builder
from digest_builder import DigestBuilder


def test_build_digests_uses_notebooklm_exports_and_writes_outputs(tmp_path, monkeypatch) -> None:
    exports_dir = tmp_path / "exports"
    digests_dir = tmp_path / "digests"
    exports_dir.mkdir()
    digests_dir.mkdir()
    monkeypatch.setattr(digest_builder, "EXPORTS_DIR", exports_dir)
    monkeypatch.setattr(digest_builder, "DIGESTS_DIR", digests_dir)

    (exports_dir / "test_topic_extraction.md").write_text(
        "| Full Title | Authors | Year |\n| --- | --- | --- |\n| Paper A | Ada | 2024 |\n",
        encoding="utf-8",
    )
    (exports_dir / "test_topic_synthesis.md").write_text("Synthesized by NotebookLM.", encoding="utf-8")
    (exports_dir / "test_topic_digest.md").write_text("Executive brief.", encoding="utf-8")
    (exports_dir / "test_topic_map.md").write_text("Research map.", encoding="utf-8")

    downloaded = pd.DataFrame(
        [
            {
                "title": "Paper A",
                "authors": "Ada",
                "year": 2024,
                "local_pdf_path": "/tmp/paper.pdf",
                "pdf_url": "https://example.org/paper.pdf",
            }
        ]
    )

    output_path = DigestBuilder().build_digests("test topic", downloaded)

    assert output_path == digests_dir / "test_topic_daily_digest.md"
    assert "Synthesized by NotebookLM." in output_path.read_text(encoding="utf-8")
    assert (digests_dir / "test_topic_executive_brief.md").read_text(encoding="utf-8") == "Executive brief."
    table = pd.read_csv(digests_dir / "test_topic_literature_table.csv")
    assert table.iloc[0]["Full Title"] == "Paper A"
