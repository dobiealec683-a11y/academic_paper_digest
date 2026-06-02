from paper_ranker import compute_keyword_overlap, rank_papers


def test_compute_keyword_overlap_weights_title_above_abstract() -> None:
    score = compute_keyword_overlap("climate governance", "Climate Governance", "governance governance")

    assert score == 16.0


def test_rank_papers_scores_and_orders_papers() -> None:
    papers = [
        {
            "title": "Unrelated",
            "abstract": "",
            "cited_by_count": 0,
            "publication_year": 2010,
            "is_oa": False,
            "pdf_url": None,
            "doi": None,
            "authors": [],
        },
        {
            "title": "Climate Governance Frameworks",
            "abstract": "Climate governance improves oversight.",
            "cited_by_count": 100,
            "publication_year": 2025,
            "is_oa": True,
            "pdf_url": "https://example.org/paper.pdf",
            "doi": "10.1/example",
            "authors": ["A. Researcher"],
        },
    ]

    ranked = rank_papers(papers, "climate governance", current_year=2026)

    assert ranked.iloc[0]["title"] == "Climate Governance Frameworks"
    assert ranked.iloc[0]["rank"] == 1
    assert ranked.iloc[0]["pdf_score"] == 10.0
    assert ranked.iloc[1]["penalty"] == -25.0
