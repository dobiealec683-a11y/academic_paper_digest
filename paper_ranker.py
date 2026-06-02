from __future__ import annotations

import logging
import math
import re
from datetime import datetime
from typing import Any

import pandas as pd

from utils import log_context

logger = logging.getLogger(__name__)


def compute_keyword_overlap(query: str, title: str | None, abstract: str | None) -> float:
    """
    Computes keyword overlap score based on query term frequency.
    """
    title = (title or "").lower()
    abstract = (abstract or "").lower()
    
    # Tokenize query into words (filter out common short stop words)
    stopwords = {
        "and",
        "of",
        "the",
        "in",
        "on",
        "for",
        "with",
        "a",
        "an",
        "to",
        "is",
        "by",
        "that",
        "this",
        "from",
    }
    query_words = [w for w in re.findall(r"\w+", query.lower()) if w not in stopwords and len(w) > 1]
    
    if not query_words:
        return 0.0
        
    score = 0.0
    for word in query_words:
        # Title matches get 3x weighting
        title_count = len(re.findall(rf"\b{re.escape(word)}\b", title))
        score += title_count * 3.0
        
        # Abstract matches get 1x weighting
        abstract_count = len(re.findall(rf"\b{re.escape(word)}\b", abstract))
        score += abstract_count * 1.0
        
    # Cap at a maximum of 40 points
    return min(40.0, score * 2.0)

def rank_papers(
    papers: list[dict[str, Any]],
    query: str,
    *,
    current_year: int | None = None,
) -> pd.DataFrame:
    """
    Ranks a list of clean papers based on multiple scoring factors.
    Returns a pandas DataFrame sorted by total score.
    """
    if not query.strip():
        raise ValueError("Paper ranking query cannot be empty.")

    scoring_year = current_year or datetime.now().year
    ranked_list: list[dict[str, Any]] = []
    
    for paper in papers:
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        citations = paper.get("cited_by_count", 0)
        pub_year = paper.get("publication_year") or scoring_year
        is_oa = paper.get("is_oa", False)
        pdf_url = paper.get("pdf_url")
        doi = paper.get("doi")
        
        # 1. Relevance Score (Max 40)
        relevance_score = compute_keyword_overlap(query, title, abstract)
        
        # 2. Citation Score (Max 25)
        # log-scaled so extremely highly cited papers don't completely drown out new papers
        citation_score = min(25.0, 5.0 * math.log(citations + 1))
        
        # 3. Recency Score (Max 15)
        # 15 points for current/future years, declining by 1 per year old, min 0
        recency_score = max(0.0, 15.0 - (scoring_year - pub_year))
        
        # 4. Open-Access Score (Max 10)
        oa_score = 10.0 if is_oa else 0.0
        
        # 5. Direct PDF Availability Score (Max 10)
        pdf_score = 10.0 if pdf_url else 0.0
        
        # 6. Penalties
        penalty = 0.0
        if not abstract:
            penalty -= 15.0
        if not doi:
            penalty -= 10.0
            
        total_score = relevance_score + citation_score + recency_score + oa_score + pdf_score + penalty
        
        # Build reason selected
        reasons = []
        if relevance_score > 20:
            reasons.append("High query word matches in title/abstract")
        if citations > 100:
            reasons.append(f"Highly cited ({citations} citations)")
        if pub_year >= scoring_year - 2:
            reasons.append("Highly recent publication")
        if is_oa and pdf_url:
            reasons.append("Direct Open-Access PDF available")
        elif is_oa:
            reasons.append("Open-access article")
            
        if not reasons:
            reasons.append("Standard matching paper")
            
        reason_selected = "; ".join(reasons)
        
        ranked_paper = {
            "total_score": round(total_score, 2),
            "relevance_score": round(relevance_score, 2),
            "citation_score": round(citation_score, 2),
            "recency_score": round(recency_score, 2),
            "oa_score": oa_score,
            "pdf_score": pdf_score,
            "penalty": penalty,
            "title": title,
            "year": pub_year,
            "citations": citations,
            "doi": doi or "N/A",
            "openalex_id": paper.get("openalex_id"),
            "abstract": abstract or "No abstract available.",
            "authors": ", ".join(paper.get("authors", [])),
            "journal_source": paper.get("journal_source", "Unknown Source"),
            "oa_url": paper.get("oa_url") or "N/A",
            "landing_page_url": paper.get("landing_page_url") or "N/A",
            "pdf_url": pdf_url or "",
            "reason_selected": reason_selected
        }
        ranked_list.append(ranked_paper)
        
    # Sort by total score descending
    ranked_list.sort(key=lambda x: x["total_score"], reverse=True)
    
    # Assign ranks
    for idx, paper in enumerate(ranked_list):
        paper["rank"] = idx + 1
        
    df = pd.DataFrame(ranked_list)
    
    # Reorder columns to match the output requirements
    cols = [
        "rank", "total_score", "title", "year", "citations", "doi", "openalex_id",
        "abstract", "authors", "journal_source", "oa_url", "landing_page_url",
        "pdf_url", "reason_selected", "relevance_score", "citation_score", 
        "recency_score", "oa_score", "pdf_score", "penalty"
    ]
    
    # Ensure columns exist even if dataframe is empty
    if df.empty:
        df = pd.DataFrame(columns=cols)
    else:
        df = df[cols]

    logger.info("Ranked papers", extra=log_context(query=query, papers=len(papers), ranked=len(df)))
    return df
