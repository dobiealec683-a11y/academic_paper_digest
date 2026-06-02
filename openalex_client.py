from __future__ import annotations

import json
import logging
from typing import Any

import requests

from config import BASE_DIR, OPENALEX_EMAIL
from utils import log_context, topic_slug

logger = logging.getLogger(__name__)


def reconstruct_abstract(abstract_inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct abstract from OpenAlex's abstract_inverted_index format."""
    if not abstract_inverted_index:
        return ""
    try:
        words_positions: list[tuple[int, str]] = []
        for word, positions in abstract_inverted_index.items():
            for pos in positions:
                words_positions.append((pos, word))
        words_positions.sort()
        return " ".join([word for _, word in words_positions])
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to reconstruct OpenAlex abstract", extra=log_context(error=str(exc)))
        return ""


def extract_pdf_url(work: dict[str, Any]) -> str | None:
    """Extract the best direct PDF URL from an OpenAlex work object."""

    primary_location = work.get("primary_location") or {}
    best_oa_location = work.get("best_oa_location") or {}
    locations = work.get("locations") or []

    for location in [best_oa_location, primary_location, *locations]:
        if not isinstance(location, dict):
            continue
        pdf_url = location.get("pdf_url")
        if pdf_url:
            return str(pdf_url)
    return None


def parse_openalex_work(work: dict[str, Any]) -> dict[str, Any]:
    """Convert an OpenAlex API work into the clean internal paper schema."""

    authors = []
    for authorship in work.get("authorships", []):
        author = (authorship or {}).get("author", {})
        name = author.get("display_name")
        if name:
            authors.append(name)

    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    open_access = work.get("open_access") or {}
    best_oa_location = work.get("best_oa_location") or {}

    return {
        "openalex_id": work.get("id"),
        "title": work.get("title") or "Untitled",
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "cited_by_count": work.get("cited_by_count", 0) or 0,
        "doi": work.get("doi"),
        "authors": authors,
        "journal_source": source.get("display_name") or "Unknown Source",
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
        "is_oa": open_access.get("is_oa", False),
        "oa_url": open_access.get("oa_url"),
        "landing_page_url": best_oa_location.get("landing_page_url")
        or primary_location.get("landing_page_url"),
        "pdf_url": extract_pdf_url(work),
    }


class OpenAlexClient:
    def __init__(self, email: str = OPENALEX_EMAIL, timeout_seconds: int = 30) -> None:
        self.email = email
        self.base_url = "https://api.openalex.org/works"
        self.timeout_seconds = timeout_seconds

    def search_works(
        self,
        query: str,
        start_year: int | None = None,
        end_year: int | None = None,
        max_results: int = 20,
        open_access_only: bool = False,
        paper_type: str | None = None,
        sort_by: str = "cited_by_count:desc",
    ) -> list[dict[str, Any]]:
        """
        Search OpenAlex works with cursor pagination.
        """
        if not query.strip():
            raise ValueError("OpenAlex search query cannot be empty.")
        if max_results < 1:
            raise ValueError("max_results must be at least 1.")

        params = {
            "search": query,
            "mailto": self.email,
            "per-page": min(max_results, 50),
            "cursor": "*",
        }

        filters: list[str] = []
        if start_year and end_year:
            filters.append(f"publication_year:{start_year}-{end_year}")
        elif start_year:
            filters.append(f"publication_year:{start_year}-")
        elif end_year:
            filters.append(f"publication_year:-{end_year}")

        if open_access_only:
            filters.append("is_oa:true")

        if paper_type:
            filters.append(f"type:{paper_type}")

        if filters:
            params["filter"] = ",".join(filters)

        if sort_by:
            params["sort"] = sort_by

        logger.info(
            "Searching OpenAlex",
            extra=log_context(query=query, max_results=max_results, open_access_only=open_access_only),
        )
        results: list[dict[str, Any]] = []
        raw_results: list[dict[str, Any]] = []
        
        while len(results) < max_results:
            try:
                response = requests.get(self.base_url, params=params, timeout=self.timeout_seconds)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise RuntimeError(
                    f"OpenAlex request failed for query '{query}': {exc}. "
                    "Check network access, your OPENALEX_EMAIL value, and OpenAlex availability."
                ) from exc
            
            data = response.json()
            works = data.get("results", [])
            if not works:
                break
            
            raw_results.extend(works)
            
            for work in works:
                results.append(parse_openalex_work(work))
                if len(results) >= max_results:
                    break

            next_cursor = data.get("meta", {}).get("next_cursor")
            if not next_cursor or next_cursor == params.get("cursor"):
                break
            params["cursor"] = next_cursor

        results = results[:max_results]
        
        cache_dir = BASE_DIR / "outputs" / "cache"
        cache_dir.mkdir(exist_ok=True)
        
        slug = topic_slug(query)
        with open(cache_dir / f"{slug}_raw.json", "w", encoding="utf-8") as f:
            json.dump(raw_results[:max_results], f, indent=2)
            
        with open(cache_dir / f"{slug}_clean.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        logger.info("OpenAlex search complete", extra=log_context(query=query, results=len(results)))
        return results

    def get_work_by_doi(self, doi: str) -> dict[str, Any]:
        """Fetch one OpenAlex work by DOI and return the clean internal paper schema."""

        normalized_doi = doi.strip()
        if not normalized_doi:
            raise ValueError("DOI cannot be empty.")

        params = {"mailto": self.email}
        url = f"{self.base_url}/doi:{normalized_doi}"
        logger.info("Fetching OpenAlex work by DOI", extra=log_context(doi=normalized_doi))
        try:
            response = requests.get(url, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"OpenAlex DOI lookup failed for '{normalized_doi}': {exc}. "
                "Check the DOI, network access, and OpenAlex availability."
            ) from exc

        raw_work = response.json()
        paper = parse_openalex_work(raw_work)

        cache_dir = BASE_DIR / "outputs" / "cache"
        cache_dir.mkdir(exist_ok=True)
        slug = topic_slug(paper["title"])
        with open(cache_dir / f"{slug}_raw.json", "w", encoding="utf-8") as f:
            json.dump(raw_work, f, indent=2)
        with open(cache_dir / f"{slug}_clean.json", "w", encoding="utf-8") as f:
            json.dump(paper, f, indent=2)

        return paper
