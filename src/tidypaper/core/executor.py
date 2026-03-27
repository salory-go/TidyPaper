"""File executor: performs rename/move operations with conflict handling."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def plan_organize(
    source_path: str,
    new_filename: str,
    target_dir: Path,
) -> tuple[Path, Path]:
    """Plan a file move without mutating disk state."""
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    dest = _resolve_conflict(target_dir / new_filename)
    return src, dest

    logger.info("Moving: %s → %s", src, dest)


def move_file(source_path: Path, target_path: Path) -> None:
    """Move a file to an exact target path."""
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Moving: %s -> %s", source_path, target_path)
    shutil.move(str(source_path), str(target_path))


def _resolve_conflict(dest: Path) -> Path:
    """If dest already exists, append (1), (2), etc. to the stem."""
    if not dest.exists():
        return dest

    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 1

    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
        if counter > 999:
            raise RuntimeError(f"Too many conflicts for: {dest}")
