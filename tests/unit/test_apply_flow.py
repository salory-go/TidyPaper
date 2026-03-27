"""Regression tests for scan/apply state handling."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from tidypaper.cli import main as cli_main
from tidypaper.db.database import Database
from tidypaper.models.paper import PaperRecord


def _write_staging(monkeypatch, home_dir: Path, entries: list[dict]) -> None:
    monkeypatch.setattr(cli_main.Path, "home", lambda: home_dir)
    staging_path = cli_main._get_staging_path()
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path.write_text(json.dumps(entries), encoding="utf-8")


def _make_preview_paper(path: Path, paper_id: str) -> PaperRecord:
    return PaperRecord(
        id=paper_id,
        source_path=str(path),
        current_path=str(path),
        file_hash=f"hash-{paper_id}",
        title="Test Paper",
        status="preview",
    )


def test_apply_does_not_create_batch_when_all_moves_fail(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    missing_path = tmp_path / "missing.pdf"
    paper = _make_preview_paper(missing_path, "paper-missing")

    db = Database(db_path)
    db.connect()
    db.insert_paper(paper)
    db.close()

    _write_staging(
        monkeypatch,
        tmp_path,
        [
            {
                "source_path": str(missing_path),
                "paper_id": paper.id,
                "confidence": 0.95,
                "new_filename": "renamed.pdf",
                "target_dir": str(tmp_path / "archive"),
                "is_duplicate": False,
            }
        ],
    )
    monkeypatch.setattr(cli_main, "_db", None)

    result = CliRunner().invoke(
        cli_main.cli,
        ["--db-path", str(db_path), "apply", "--yes"],
    )

    assert result.exit_code == 0, result.output
    assert "No undo batch was created." in result.output

    db = Database(db_path)
    db.connect()
    assert db.get_latest_batch() is None
    assert db.conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 0
    db.close()


def test_apply_rolls_back_file_when_db_write_fails(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    source_path = tmp_path / "paper.pdf"
    source_path.write_bytes(b"pdf")
    archive_dir = tmp_path / "archive"
    target_path = archive_dir / "renamed.pdf"
    paper = _make_preview_paper(source_path, "paper-rollback")

    db = Database(db_path)
    db.connect()
    db.insert_paper(paper)
    db.close()

    _write_staging(
        monkeypatch,
        tmp_path,
        [
            {
                "source_path": str(source_path),
                "paper_id": paper.id,
                "confidence": 0.95,
                "new_filename": "renamed.pdf",
                "target_dir": str(archive_dir),
                "is_duplicate": False,
            }
        ],
    )
    monkeypatch.setattr(cli_main, "_db", None)

    def fail_persist(self, op, stored_paper, *, batch=None):
        raise sqlite3.IntegrityError("simulated failure")

    monkeypatch.setattr(Database, "persist_applied_operation", fail_persist)

    result = CliRunner().invoke(
        cli_main.cli,
        ["--db-path", str(db_path), "apply", "--yes"],
    )

    assert result.exit_code == 0, result.output
    assert source_path.exists()
    assert not target_path.exists()

    db = Database(db_path)
    db.connect()
    assert db.conn.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 0
    assert db.conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 0

    stored = db.get_paper_by_id(paper.id)
    assert stored is not None
    assert stored.current_path == str(source_path)
    assert stored.status == "preview"
    db.close()
