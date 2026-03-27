"""Undo support: revert a batch of file operations."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from tidypaper.db.database import Database
from tidypaper.models.paper import PaperRecord

logger = logging.getLogger(__name__)


@dataclass
class UndoResult:
    """Result of undoing a single operation."""

    old_path: str
    new_path: str
    success: bool
    error: str = ""
    already_reverted: bool = False


def undo_latest_batch(db: Database) -> list[UndoResult]:
    """Undo the most recent executed batch.

    Returns a list of UndoResult indicating success/failure for each operation.
    """
    batch = db.get_latest_batch()
    if batch is None:
        logger.warning("No executed batch found to undo")
        return []

    return undo_batch(batch.batch_id, db)


def undo_batch(batch_id: str, db: Database) -> list[UndoResult]:
    """Undo all operations in a specific batch."""
    ops = db.get_batch_operations(batch_id)
    if not ops:
        logger.warning("No operations found for batch %s", batch_id)
        return []

    results: list[UndoResult] = []
    reverted_papers: list[PaperRecord] = []

    for op in ops:
        result = _undo_single(op.old_path, op.new_path)
        results.append(result)
        if result.success:
            paper = db.get_paper_by_id(op.paper_id)
            if paper is not None:
                paper.current_path = op.old_path
                paper.status = "preview"
                reverted_papers.append(paper)

    all_succeeded = all(r.success for r in results)
    if reverted_papers or all_succeeded:
        db.persist_undo_results(
            batch_id,
            reverted_papers,
            mark_batch_undone=all_succeeded,
        )

    successes = sum(1 for r in results if r.success)
    logger.info("Undo batch %s: %d/%d operations reversed", batch_id, successes, len(results))

    return results


def _undo_single(old_path: str, new_path: str) -> UndoResult:
    """Reverse a single file move."""
    src = Path(new_path)
    dest = Path(old_path)

    if not src.exists():
        if dest.exists():
            return UndoResult(
                old_path=old_path,
                new_path=new_path,
                success=True,
                already_reverted=True,
            )
        return UndoResult(
            old_path=old_path, new_path=new_path,
            success=False, error=f"Current file not found: {new_path}",
        )

    try:
        # Ensure the original directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        logger.info("Reverted: %s → %s", src, dest)
        return UndoResult(old_path=old_path, new_path=new_path, success=True)
    except OSError as exc:
        return UndoResult(
            old_path=old_path, new_path=new_path,
            success=False, error=str(exc),
        )
