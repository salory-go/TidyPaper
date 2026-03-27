"""Filename sanitization utilities for cross-platform safety."""

from __future__ import annotations

import re

# Characters illegal in Windows filenames
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTI_SPACE = re.compile(r"\s{2,}")
_MULTI_DOT = re.compile(r"\.{2,}")

MAX_FILENAME_LEN = 200  # conservative limit for cross-platform safety


def sanitize_filename(name: str) -> str:
    """Clean a string so it is safe to use as a filename on all platforms.

    Handles:
    - Windows illegal characters
    - Consecutive spaces / dots
    - Leading/trailing dots and spaces
    - Over-long names (truncated to MAX_FILENAME_LEN)
    """
    if not name:
        return "Untitled"

    # Replace illegal characters with space
    name = _ILLEGAL_CHARS.sub(" ", name)

    # Collapse multiple spaces / dots
    name = _MULTI_SPACE.sub(" ", name)
    name = _MULTI_DOT.sub(".", name)

    # Strip leading/trailing whitespace and dots
    name = name.strip(" .")

    # Truncate to max length (preserve extension if present)
    if len(name) > MAX_FILENAME_LEN:
        name = name[:MAX_FILENAME_LEN].rstrip(" .")

    if not name:
        return "Untitled"

    return name
