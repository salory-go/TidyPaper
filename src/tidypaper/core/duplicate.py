"""Duplicate detection across multiple signal layers."""

from __future__ import annotations

from dataclasses import dataclass

from tidypaper.core.parser import _jaccard_words
from tidypaper.db.database import Database
from tidypaper.models.paper import PaperRecord

_TITLE_SIMILARITY_THRESHOLD = 0.7


@dataclass
class DuplicateResult:
    """Result of a duplicate check."""

    is_duplicate: bool
    match_type: str = ""  # "hash" | "doi" | "arxiv_id" | "title"
    existing_paper_id: str = ""
    existing_title: str = ""
    similarity: float = 0.0


def check_duplicate(paper: PaperRecord, db: Database) -> DuplicateResult:
    """Check if a paper is a duplicate by hash, DOI, arXiv ID, or title similarity.

    Returns DuplicateResult with match details.
    """
    exclude_statuses = ("preview",)

    # Layer 1: exact hash match
    existing = db.get_paper_by_hash(paper.file_hash, exclude_statuses=exclude_statuses)
    if existing and existing.id != paper.id:
        return DuplicateResult(
            is_duplicate=True,
            match_type="hash",
            existing_paper_id=existing.id,
            existing_title=existing.title,
            similarity=1.0,
        )

    # Layer 2: DOI match
    if paper.doi:
        existing = db.get_paper_by_doi(paper.doi, exclude_statuses=exclude_statuses)
        if existing and existing.id != paper.id:
            return DuplicateResult(
                is_duplicate=True,
                match_type="doi",
                existing_paper_id=existing.id,
                existing_title=existing.title,
                similarity=1.0,
            )

    # Layer 3: arXiv ID match
    if paper.arxiv_id:
        existing = db.get_paper_by_arxiv_id(paper.arxiv_id, exclude_statuses=exclude_statuses)
        if existing and existing.id != paper.id:
            return DuplicateResult(
                is_duplicate=True,
                match_type="arxiv_id",
                existing_paper_id=existing.id,
                existing_title=existing.title,
                similarity=1.0,
            )

    # Layer 4: title similarity
    if paper.title:
        all_papers = db.get_all_papers(exclude_statuses=exclude_statuses)
        for p in all_papers:
            if p.id == paper.id or not p.title:
                continue
            candidate_title = p.title.lower()
            sim = _jaccard_words(paper.title.lower(), candidate_title)
            if sim >= _TITLE_SIMILARITY_THRESHOLD:
                return DuplicateResult(
                    is_duplicate=True,
                    match_type="title",
                    existing_paper_id=p.id,
                    existing_title=p.title,
                    similarity=round(sim, 3),
                )

    return DuplicateResult(is_duplicate=False)
