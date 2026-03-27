"""Data models for paper records and PDF parse results."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TitleCandidate:
    """A candidate title extracted from a PDF with a confidence score."""

    text: str
    score: float = 0.0


@dataclass
class PdfParseResult:
    """Raw result from parsing a single PDF file."""

    file_path: str
    file_hash: str
    title_candidates: list[TitleCandidate] = field(default_factory=list)
    raw_text_first_pages: str = ""
    pdf_metadata: dict[str, str] = field(default_factory=dict)
    doi: str | None = None
    arxiv_id: str | None = None
    venue_hints: list[str] = field(default_factory=list)

    @property
    def best_title(self) -> str | None:
        """Return the highest-scoring title candidate, if any."""
        if not self.title_candidates:
            return None
        return max(self.title_candidates, key=lambda c: c.score).text


@dataclass
class PaperRecord:
    """Normalized paper record after metadata fusion."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str = ""
    current_path: str = ""
    file_hash: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    first_author: str = ""
    year: int | None = None
    venue: str = ""
    paper_type: str = ""  # "conference" | "journal" | "preprint" | ""
    doi: str | None = None
    arxiv_id: str | None = None
    confidence: float = 0.0
    status: str = "pending"  # "pending" | "preview" | "organized" | "failed"
    evidence: dict[str, Any] = field(default_factory=dict)
