"""Metadata fusion: combine results from multiple sources into a single PaperRecord."""

from __future__ import annotations

import logging
from typing import Any

from tidypaper.core.parser import _jaccard_words
from tidypaper.models.paper import PaperRecord, PdfParseResult
from tidypaper.providers.base import MetadataResult

logger = logging.getLogger(__name__)


def merge_metadata(
    pdf_result: PdfParseResult,
    provider_results: list[MetadataResult],
) -> PaperRecord:
    """Fuse PDF parse output with external provider results.

    Returns a PaperRecord with a computed confidence score and evidence trail.
    """
    evidence: dict[str, Any] = {"pdf": {}, "providers": []}

    # ── Start with PDF-extracted data ────────────────────
    best_title = pdf_result.best_title or ""
    doi = pdf_result.doi
    arxiv_id = pdf_result.arxiv_id

    evidence["pdf"] = {
        "title_candidates": len(pdf_result.title_candidates),
        "best_title": best_title,
        "doi": doi,
        "arxiv_id": arxiv_id,
    }

    # ── Pick the best provider result ────────────────────
    chosen: MetadataResult | None = None
    for pr in provider_results:
        if pr is None or pr.is_empty:
            continue
        evidence["providers"].append({
            "provider": pr.provider,
            "title": pr.title,
            "doi": pr.doi,
            "year": pr.year,
            "venue": pr.venue,
        })
        if chosen is None:
            chosen = pr

    # ── Fuse fields ──────────────────────────────────────
    title = ""
    authors: list[str] = []
    first_author = ""
    year: int | None = None
    venue = ""
    paper_type = ""

    if chosen:
        title = chosen.title or best_title
        authors = chosen.authors or []
        first_author = chosen.first_author or ""
        year = chosen.year
        venue = chosen.venue or ""
        paper_type = chosen.paper_type or ""
        doi = chosen.doi or doi
        arxiv_id = chosen.arxiv_id or arxiv_id
    else:
        title = best_title

    # ── Compute confidence ───────────────────────────────
    confidence = _compute_confidence(
        pdf_result=pdf_result,
        chosen=chosen,
        title=title,
        doi=doi,
        arxiv_id=arxiv_id,
        venue=venue,
        year=year,
    )
    evidence["confidence_breakdown"] = confidence["breakdown"]

    return PaperRecord(
        source_path=pdf_result.file_path,
        current_path=pdf_result.file_path,
        file_hash=pdf_result.file_hash,
        title=title,
        authors=authors,
        first_author=first_author,
        year=year,
        venue=venue,
        paper_type=paper_type,
        doi=doi,
        arxiv_id=arxiv_id,
        confidence=confidence["score"],
        status="preview",
        evidence=evidence,
    )


def _compute_confidence(
    *,
    pdf_result: PdfParseResult,
    chosen: MetadataResult | None,
    title: str,
    doi: str | None,
    arxiv_id: str | None,
    venue: str,
    year: int | None,
) -> dict[str, Any]:
    """Compute a confidence score based on evidence signals."""
    score = 0.0
    breakdown: dict[str, float] = {}

    # DOI hit
    if doi and chosen and chosen.doi:
        score += 0.45
        breakdown["doi_hit"] = 0.45

    # arXiv ID hit
    elif arxiv_id and chosen and chosen.arxiv_id:
        score += 0.45
        breakdown["arxiv_hit"] = 0.45

    # Title match between PDF and provider
    if chosen and chosen.title and pdf_result.best_title:
        sim = _jaccard_words(chosen.title.lower(), pdf_result.best_title.lower())
        if sim > 0.6:
            bonus = 0.20
            score += bonus
            breakdown["title_match"] = bonus
        elif sim < 0.2:
            penalty = -0.20
            score += penalty
            breakdown["title_conflict"] = penalty

    # Venue match
    if venue:
        score += 0.10
        breakdown["venue_present"] = 0.10

    # Year present
    if year:
        score += 0.05
        breakdown["year_present"] = 0.05

    # No provider results at all
    if chosen is None:
        score += 0.10  # base from PDF only
        breakdown["pdf_only"] = 0.10

    # Title quality check
    if title:
        words = len(title.split())
        if words < 3:
            score -= 0.10
            breakdown["title_too_short"] = -0.10
    else:
        score -= 0.30
        breakdown["no_title"] = -0.30

    score = max(0.0, min(1.0, score))
    return {"score": round(score, 2), "breakdown": breakdown}
