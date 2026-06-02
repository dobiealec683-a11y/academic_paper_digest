from openalex_client import extract_pdf_url, parse_openalex_work, reconstruct_abstract


def test_reconstruct_abstract_orders_inverted_index_positions() -> None:
    inverted = {"world": [1], "Hello": [0], "again": [2]}

    assert reconstruct_abstract(inverted) == "Hello world again"


def test_parse_openalex_work_extracts_clean_schema() -> None:
    work = {
        "id": "https://openalex.org/W1",
        "title": "Transformer Governance",
        "publication_year": 2024,
        "publication_date": "2024-01-02",
        "cited_by_count": 42,
        "doi": "https://doi.org/10.1/example",
        "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
        "abstract_inverted_index": {"AI": [0], "governance": [1]},
        "primary_location": {
            "source": {"display_name": "Journal of Tests"},
            "landing_page_url": "https://example.org/article",
        },
        "best_oa_location": {"pdf_url": "https://example.org/paper.pdf"},
        "open_access": {"is_oa": True, "oa_url": "https://example.org/oa"},
    }

    parsed = parse_openalex_work(work)

    assert parsed["title"] == "Transformer Governance"
    assert parsed["authors"] == ["Ada Lovelace"]
    assert parsed["abstract"] == "AI governance"
    assert parsed["journal_source"] == "Journal of Tests"
    assert parsed["pdf_url"] == "https://example.org/paper.pdf"
    assert parsed["is_oa"] is True


def test_extract_pdf_url_checks_locations_fallback() -> None:
    work = {
        "primary_location": {},
        "best_oa_location": {},
        "locations": [{"pdf_url": "https://cdn.example/paper.pdf"}],
    }

    assert extract_pdf_url(work) == "https://cdn.example/paper.pdf"
