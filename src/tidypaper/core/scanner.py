"""Directory scanner for batch PDF processing."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def scan_directory(directory: str | Path, recursive: bool = True) -> list[Path]:
    """Scan a directory and return all PDF file paths.

    Args:
        directory: Path to scan.
        recursive: If True, scan subdirectories as well.

    Returns:
        List of Path objects for each PDF found, sorted by name.
    """
    root = Path(directory)
    if not root.exists():
        logger.error("Directory does not exist: %s", root)
        return []

    if not root.is_dir():
        logger.error("Path is not a directory: %s", root)
        return []

    pattern = "**/*.pdf" if recursive else "*.pdf"
    pdfs = sorted(root.glob(pattern))

    logger.info("Found %d PDF files in %s", len(pdfs), root)
    return pdfs
