"""Archive path generation from paper metadata."""

from __future__ import annotations

from pathlib import Path

from tidypaper.models.paper import PaperRecord
from tidypaper.utils.filename import sanitize_filename

_DEFAULT_FOLDER_TEMPLATE = "{year}/{venue}"
_UNSORTED = "Unsorted"


def generate_archive_path(
    paper: PaperRecord,
    archive_root: str,
    folder_template: str = _DEFAULT_FOLDER_TEMPLATE,
    unsorted_name: str = _UNSORTED,
    confidence_threshold: float = 0.60,
) -> Path:
    """Generate the target archive directory path.

    If confidence is below the threshold, routes to the Unsorted folder.
    """
    root = Path(archive_root)

    if paper.confidence < confidence_threshold:
        return root / unsorted_name

    year_str = str(paper.year) if paper.year else "Unknown"
    venue_str = sanitize_filename(paper.venue) if paper.venue else "Unknown"
    paper_type_str = paper.paper_type or "paper"

    folder_name = folder_template.format(
        year=year_str,
        venue=venue_str,
        paper_type=paper_type_str,
    )

    return root / folder_name
