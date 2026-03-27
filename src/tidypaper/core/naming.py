"""Filename generation from paper metadata."""

from __future__ import annotations

from tidypaper.models.paper import PaperRecord
from tidypaper.utils.filename import sanitize_filename

_DEFAULT_TEMPLATE = "{year} - {venue} - {title}"


def generate_filename(paper: PaperRecord, template: str = _DEFAULT_TEMPLATE) -> str:
    """Generate a standardized filename from paper metadata.

    Template variables: {title}, {year}, {venue}, {first_author}, {paper_type}
    Missing variables are handled gracefully (omitted from the name).
    """
    year_str = str(paper.year) if paper.year else "Unknown"
    venue_str = paper.venue or "Unknown"
    title_str = paper.title or "Untitled"
    first_author_str = paper.first_author or "Unknown"
    paper_type_str = paper.paper_type or "paper"

    # Build the filename from template
    name = template.format(
        year=year_str,
        venue=venue_str,
        title=title_str,
        first_author=first_author_str,
        paper_type=paper_type_str,
    )

    # Clean up "Unknown" segments: e.g. "Unknown - Unknown - Title" → "Title"
    parts = [p.strip() for p in name.split(" - ")]
    parts = [p for p in parts if p and p != "Unknown"]
    if parts:
        name = " - ".join(parts)
    else:
        name = title_str

    name = sanitize_filename(name)
    return f"{name}.pdf"
