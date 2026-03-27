"""PDF parsing and title extraction using PyMuPDF."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import fitz  # PyMuPDF

from tidypaper.models.paper import PdfParseResult, TitleCandidate

# ── Constants ───────────────────────────────────────────────

_MAX_PAGES_TO_PARSE = 3
_HASH_BUF_SIZE = 65536

# Scoring weights
_SCORE_POSITION_TOP = 0.20      # block in upper 30% of page
_SCORE_FONT_LARGE = 0.25        # font size significantly above mean
_SCORE_LENGTH_GOOD = 0.15       # 5-30 words
_SCORE_ACADEMIC = 0.15          # looks like an academic title
_SCORE_PDF_META_MATCH = 0.10    # matches PDF metadata title

_PENALTY_ABSTRACT = -0.30
_PENALTY_EMAIL = -0.25
_PENALTY_COPYRIGHT = -0.20
_PENALTY_ALL_CAPS_SHORT = -0.20
_PENALTY_INSTITUTION = -0.15
_PENALTY_TOO_SHORT = -0.20
_PENALTY_TOO_LONG = -0.15

# Patterns
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_ABSTRACT_RE = re.compile(r"\babstract\b", re.IGNORECASE)
_COPYRIGHT_RE = re.compile(r"(©|\bcopyright\b|\(c\)|978-|ISBN)", re.IGNORECASE)
_INSTITUTION_RE = re.compile(
    r"\b(university|institute|department|college|laboratory|lab|school of)\b",
    re.IGNORECASE,
)


def compute_file_hash(path: str | Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(_HASH_BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def parse_pdf(path: str | Path) -> PdfParseResult:
    """Parse a PDF file and extract title candidates, text, and metadata."""
    path = Path(path)
    file_hash = compute_file_hash(path)

    doc = fitz.open(str(path))
    try:
        pdf_metadata = _extract_pdf_metadata(doc)
        blocks = _extract_text_blocks(doc)
        raw_text = _extract_raw_text(doc)
        title_candidates = _score_title_candidates(blocks, pdf_metadata)

        return PdfParseResult(
            file_path=str(path),
            file_hash=file_hash,
            title_candidates=title_candidates,
            raw_text_first_pages=raw_text,
            pdf_metadata=pdf_metadata,
        )
    finally:
        doc.close()


# ── Internal helpers ────────────────────────────────────────


def _extract_pdf_metadata(doc: fitz.Document) -> dict[str, str]:
    """Extract metadata from the PDF info dict."""
    meta = doc.metadata or {}
    return {k: str(v).strip() for k, v in meta.items() if v}


def _extract_raw_text(doc: fitz.Document) -> str:
    """Extract plain text from the first N pages."""
    parts: list[str] = []
    for page_num in range(min(len(doc), _MAX_PAGES_TO_PARSE)):
        page = doc[page_num]
        parts.append(page.get_text("text"))
    return "\n".join(parts)


def _extract_text_blocks(doc: fitz.Document) -> list[dict]:
    """Extract text blocks from page 0 with position & font info."""
    if len(doc) == 0:
        return []

    page = doc[0]
    page_height = page.rect.height
    blocks_raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

    blocks: list[dict] = []
    for block in blocks_raw:
        if block.get("type") != 0:  # text blocks only
            continue
        lines = block.get("lines", [])
        if not lines:
            continue

        # Gather text and max font size from all spans
        text_parts: list[str] = []
        max_font_size = 0.0
        for line in lines:
            for span in line.get("spans", []):
                text_parts.append(span.get("text", ""))
                fs = span.get("size", 0.0)
                if fs > max_font_size:
                    max_font_size = fs

        full_text = " ".join(text_parts).strip()
        if not full_text:
            continue

        y_top = block.get("bbox", [0, 0, 0, 0])[1]
        blocks.append({
            "text": full_text,
            "y_top": y_top,
            "page_height": page_height,
            "font_size": max_font_size,
        })

    return blocks


def _score_title_candidates(
    blocks: list[dict],
    pdf_metadata: dict[str, str],
) -> list[TitleCandidate]:
    """Score each text block as a potential paper title."""
    if not blocks:
        return []

    # Compute average font size for relative comparison
    font_sizes = [b["font_size"] for b in blocks if b["font_size"] > 0]
    avg_font = sum(font_sizes) / len(font_sizes) if font_sizes else 12.0

    pdf_title = pdf_metadata.get("title", "").strip().lower()

    candidates: list[TitleCandidate] = []

    for block in blocks:
        text = block["text"]
        score = 0.5  # base score

        word_count = len(text.split())
        y_ratio = block["y_top"] / block["page_height"] if block["page_height"] > 0 else 1.0

        # ── Positive signals ──
        if y_ratio < 0.30:
            score += _SCORE_POSITION_TOP
        if block["font_size"] > avg_font * 1.3:
            score += _SCORE_FONT_LARGE
        if 5 <= word_count <= 30:
            score += _SCORE_LENGTH_GOOD
        if pdf_title and _fuzzy_match(text.lower(), pdf_title):
            score += _SCORE_PDF_META_MATCH
        # Simple academic heuristic: has enough words, mixed case
        if word_count >= 4 and not text.isupper():
            score += _SCORE_ACADEMIC

        # ── Negative signals ──
        if _ABSTRACT_RE.search(text):
            score += _PENALTY_ABSTRACT
        if _EMAIL_RE.search(text):
            score += _PENALTY_EMAIL
        if _COPYRIGHT_RE.search(text):
            score += _PENALTY_COPYRIGHT
        if _INSTITUTION_RE.search(text):
            score += _PENALTY_INSTITUTION
        if text.isupper() and word_count < 10:
            score += _PENALTY_ALL_CAPS_SHORT
        if word_count < 3:
            score += _PENALTY_TOO_SHORT
        if word_count > 40:
            score += _PENALTY_TOO_LONG

        score = max(0.0, min(1.0, score))
        candidates.append(TitleCandidate(text=text, score=round(score, 3)))

    # Sort by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _fuzzy_match(a: str, b: str) -> bool:
    """Simple containment-based fuzzy match."""
    if not a or not b:
        return False
    # Check if the shorter is contained in the longer
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return short in long or _jaccard_words(a, b) > 0.6


def _jaccard_words(a: str, b: str) -> float:
    """Word-level Jaccard similarity."""
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
