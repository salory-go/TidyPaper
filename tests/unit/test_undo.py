"""Regression tests for undo batch state management."""

from __future__ import annotations

from pathlib import Path

import pytest

from tidypaper.core.undo import undo_batch
from tidypaper.db.database import Database
from tidypaper.models.operation import BatchRecord, OperationRecord
from tidypaper.models.paper import PaperRecord


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    database.connect()
    yield database
    database.close()


def _make_paper(paper_id: str, source_path: Path, current_path: Path, file_hash: str) -> PaperRecord:
    return PaperRecord(
        id=paper_id,
        source_path=str(source_path),
        current_path=str(current_path),
        file_hash=file_hash,
        title=f"Paper {paper_id}",
        status="organized",
    )


def test_get_latest_batch_skips_empty_executed_batch(db, tmp_path):
    source_path = tmp_path / "source.pdf"
    current_path = tmp_path / "archive" / "paper.pdf"
    paper = _make_paper("paper-real", source_path, current_path, "hash-real")
    db.insert_paper(paper)

    real_batch = BatchRecord()
    db.create_batch(real_batch)
    db.insert_operation(
        OperationRecord(
            batch_id=real_batch.batch_id,
            paper_id=paper.id,
            old_path=str(source_path),
            new_path=str(current_path),
        )
    )
    db.update_batch_count(real_batch.batch_id, 1)

    empty_batch = BatchRecord()
    db.create_batch(empty_batch)

    latest = db.get_latest_batch()
    assert latest is not None
    assert latest.batch_id == real_batch.batch_id


def test_undo_partial_failure_keeps_batch_executed_and_can_retry(db, tmp_path):
    source_one = tmp_path / "source-one.pdf"
    source_two = tmp_path / "source-two.pdf"
    new_one = tmp_path / "archive" / "paper-one.pdf"
    new_two = tmp_path / "archive" / "paper-two.pdf"
    new_one.parent.mkdir(parents=True, exist_ok=True)
    new_one.write_bytes(b"one")

    paper_one = _make_paper("paper-one", source_one, new_one, "hash-one")
    paper_two = _make_paper("paper-two", source_two, new_two, "hash-two")
    db.insert_paper(paper_one)
    db.insert_paper(paper_two)

    batch = BatchRecord()
    db.create_batch(batch)
    db.insert_operation(
        OperationRecord(
            batch_id=batch.batch_id,
            paper_id=paper_one.id,
            old_path=str(source_one),
            new_path=str(new_one),
        )
    )
    db.insert_operation(
        OperationRecord(
            batch_id=batch.batch_id,
            paper_id=paper_two.id,
            old_path=str(source_two),
            new_path=str(new_two),
        )
    )
    db.update_batch_count(batch.batch_id, 2)

    results = undo_batch(batch.batch_id, db)

    assert len(results) == 2
    assert sum(result.success for result in results) == 1
    assert db.get_latest_batch() is not None
    assert db.get_latest_batch().batch_id == batch.batch_id

    stored_one = db.get_paper_by_id(paper_one.id)
    stored_two = db.get_paper_by_id(paper_two.id)
    assert stored_one is not None
    assert stored_two is not None
    assert stored_one.current_path == str(source_one)
    assert stored_one.status == "preview"
    assert stored_two.current_path == str(new_two)
    assert stored_two.status == "organized"
    assert source_one.exists()
    assert not new_one.exists()

    new_two.write_bytes(b"two")
    retry_results = undo_batch(batch.batch_id, db)

    assert len(retry_results) == 2
    assert all(result.success for result in retry_results)
    assert any(result.already_reverted for result in retry_results)
    assert db.get_latest_batch() is None
    assert db.conn.execute(
        "SELECT status FROM batches WHERE batch_id=?",
        (batch.batch_id,),
    ).fetchone()[0] == "undone"

    stored_two = db.get_paper_by_id(paper_two.id)
    assert stored_two is not None
    assert stored_two.current_path == str(source_two)
    assert stored_two.status == "preview"
    assert source_two.exists()
    assert not new_two.exists()
