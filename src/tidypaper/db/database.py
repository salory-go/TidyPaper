"""SQLite database layer for TidyPaper."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from tidypaper.models.operation import BatchRecord, OperationRecord
from tidypaper.models.paper import PaperRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id          TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    current_path TEXT NOT NULL,
    file_hash   TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    authors     TEXT NOT NULL DEFAULT '[]',
    first_author TEXT NOT NULL DEFAULT '',
    year        INTEGER,
    venue       TEXT NOT NULL DEFAULT '',
    paper_type  TEXT NOT NULL DEFAULT '',
    doi         TEXT,
    arxiv_id    TEXT,
    confidence  REAL NOT NULL DEFAULT 0.0,
    status      TEXT NOT NULL DEFAULT 'pending',
    evidence    TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_papers_hash ON papers(file_hash);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_arxiv ON papers(arxiv_id);

CREATE TABLE IF NOT EXISTS batches (
    batch_id    TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'executed',
    operation_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS operations (
    id          TEXT PRIMARY KEY,
    batch_id    TEXT NOT NULL,
    paper_id    TEXT NOT NULL,
    old_path    TEXT NOT NULL,
    new_path    TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    FOREIGN KEY (batch_id) REFERENCES batches(batch_id),
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);

CREATE INDEX IF NOT EXISTS idx_operations_batch ON operations(batch_id);

CREATE TABLE IF NOT EXISTS duplicates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id    TEXT NOT NULL,
    duplicate_of TEXT NOT NULL,
    match_type  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);
"""


class Database:
    """SQLite database manager for TidyPaper."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".tidypaper" / "tidypaper.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ── Connection ──────────────────────────────────────────

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.connect()
        assert self._conn is not None
        return self._conn

    # ── Papers ──────────────────────────────────────────────

    def insert_paper(self, paper: PaperRecord) -> None:
        self._insert_paper(paper)
        self.conn.commit()

    def _insert_paper(self, paper: PaperRecord) -> None:
        self.conn.execute(
            """INSERT INTO papers
               (id, source_path, current_path, file_hash, title, authors,
                first_author, year, venue, paper_type, doi, arxiv_id,
                confidence, status, evidence)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                paper.id,
                paper.source_path,
                paper.current_path,
                paper.file_hash,
                paper.title,
                json.dumps(paper.authors),
                paper.first_author,
                paper.year,
                paper.venue,
                paper.paper_type,
                paper.doi,
                paper.arxiv_id,
                paper.confidence,
                paper.status,
                json.dumps(paper.evidence),
            ),
        )

    def update_paper(self, paper: PaperRecord) -> None:
        self._update_paper(paper)
        self.conn.commit()

    def _update_paper(self, paper: PaperRecord) -> None:
        cursor = self.conn.execute(
            """UPDATE papers SET
               current_path=?, title=?, authors=?, first_author=?,
               year=?, venue=?, paper_type=?, doi=?, arxiv_id=?,
               confidence=?, status=?, evidence=?
               WHERE id=?""",
            (
                paper.current_path,
                paper.title,
                json.dumps(paper.authors),
                paper.first_author,
                paper.year,
                paper.venue,
                paper.paper_type,
                paper.doi,
                paper.arxiv_id,
                paper.confidence,
                paper.status,
                json.dumps(paper.evidence),
                paper.id,
            ),
        )
        if cursor.rowcount == 0:
            raise LookupError(f"Paper not found: {paper.id}")

    def upsert_preview_paper(self, paper: PaperRecord) -> None:
        existing = self.get_preview_paper_by_source_path(paper.source_path)
        if existing is None:
            self.insert_paper(paper)
            return

        paper.id = existing.id
        paper.status = "preview"
        self.update_paper(paper)

    def get_paper_by_id(self, paper_id: str) -> PaperRecord | None:
        row = self.conn.execute(
            "SELECT * FROM papers WHERE id=?",
            (paper_id,),
        ).fetchone()
        return self._row_to_paper(row) if row else None

    def get_preview_paper_by_source_path(self, source_path: str) -> PaperRecord | None:
        row = self.conn.execute(
            """SELECT * FROM papers
               WHERE source_path=? AND status='preview'
               ORDER BY rowid DESC
               LIMIT 1""",
            (source_path,),
        ).fetchone()
        return self._row_to_paper(row) if row else None

    def get_paper_by_hash(
        self,
        file_hash: str,
        *,
        include_statuses: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ) -> PaperRecord | None:
        row = self._fetch_single_paper(
            "SELECT * FROM papers WHERE file_hash=?",
            [file_hash],
            include_statuses=include_statuses,
            exclude_statuses=exclude_statuses,
        )
        return self._row_to_paper(row) if row else None

    def get_paper_by_doi(
        self,
        doi: str,
        *,
        include_statuses: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ) -> PaperRecord | None:
        row = self._fetch_single_paper(
            "SELECT * FROM papers WHERE doi=?",
            [doi],
            include_statuses=include_statuses,
            exclude_statuses=exclude_statuses,
        )
        return self._row_to_paper(row) if row else None

    def get_paper_by_arxiv_id(
        self,
        arxiv_id: str,
        *,
        include_statuses: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ) -> PaperRecord | None:
        row = self._fetch_single_paper(
            "SELECT * FROM papers WHERE arxiv_id=?",
            [arxiv_id],
            include_statuses=include_statuses,
            exclude_statuses=exclude_statuses,
        )
        return self._row_to_paper(row) if row else None

    def get_all_papers(
        self,
        *,
        include_statuses: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ) -> list[PaperRecord]:
        query, params = self._apply_status_filters(
            "SELECT * FROM papers",
            [],
            include_statuses=include_statuses,
            exclude_statuses=exclude_statuses,
        )
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_paper(row) for row in rows]

    # ── Batches & Operations ───────────────────────────────

    def create_batch(self, batch: BatchRecord) -> None:
        self._create_batch(batch)
        self.conn.commit()

    def _create_batch(self, batch: BatchRecord) -> None:
        self.conn.execute(
            """INSERT INTO batches (batch_id, created_at, status, operation_count)
               VALUES (?,?,?,?)""",
            (batch.batch_id, batch.created_at, batch.status, batch.operation_count),
        )

    def insert_operation(self, op: OperationRecord) -> None:
        self._insert_operation(op)
        self.conn.commit()

    def _insert_operation(self, op: OperationRecord) -> None:
        self.conn.execute(
            """INSERT INTO operations (id, batch_id, paper_id, old_path, new_path, executed_at)
               VALUES (?,?,?,?,?,?)""",
            (op.id, op.batch_id, op.paper_id, op.old_path, op.new_path, op.executed_at),
        )

    def get_latest_batch(self) -> BatchRecord | None:
        row = self.conn.execute(
            """SELECT * FROM batches
               WHERE status='executed' AND operation_count > 0
               ORDER BY created_at DESC
               LIMIT 1"""
        ).fetchone()
        if not row:
            return None
        return BatchRecord(
            batch_id=row["batch_id"],
            created_at=row["created_at"],
            status=row["status"],
            operation_count=row["operation_count"],
        )

    def get_batch_operations(self, batch_id: str) -> list[OperationRecord]:
        rows = self.conn.execute(
            """SELECT * FROM operations
               WHERE batch_id=?
               ORDER BY executed_at DESC""",
            (batch_id,),
        ).fetchall()
        return [
            OperationRecord(
                id=r["id"], batch_id=r["batch_id"], paper_id=r["paper_id"],
                old_path=r["old_path"], new_path=r["new_path"],
                executed_at=r["executed_at"],
            )
            for r in rows
        ]

    def update_batch_status(self, batch_id: str, status: str) -> None:
        self._update_batch_status(batch_id, status)
        self.conn.commit()

    def _update_batch_status(self, batch_id: str, status: str) -> None:
        cursor = self.conn.execute(
            "UPDATE batches SET status=? WHERE batch_id=?",
            (status, batch_id),
        )
        if cursor.rowcount == 0:
            raise LookupError(f"Batch not found: {batch_id}")

    def update_batch_count(self, batch_id: str, count: int) -> None:
        self._update_batch_count(batch_id, count)
        self.conn.commit()

    def _update_batch_count(self, batch_id: str, count: int) -> None:
        cursor = self.conn.execute(
            "UPDATE batches SET operation_count=? WHERE batch_id=?",
            (count, batch_id),
        )
        if cursor.rowcount == 0:
            raise LookupError(f"Batch not found: {batch_id}")

    def persist_applied_operation(
        self,
        op: OperationRecord,
        paper: PaperRecord,
        *,
        batch: BatchRecord | None = None,
    ) -> None:
        with self.conn:
            if batch is not None:
                batch.operation_count = 1
                self._create_batch(batch)
            else:
                cursor = self.conn.execute(
                    """UPDATE batches
                       SET operation_count = operation_count + 1
                       WHERE batch_id=?""",
                    (op.batch_id,),
                )
                if cursor.rowcount == 0:
                    raise LookupError(f"Batch not found: {op.batch_id}")

            self._insert_operation(op)
            self._update_paper(paper)

    def persist_undo_results(
        self,
        batch_id: str,
        reverted_papers: list[PaperRecord],
        *,
        mark_batch_undone: bool,
    ) -> None:
        with self.conn:
            for paper in reverted_papers:
                self._update_paper(paper)
            if mark_batch_undone:
                self._update_batch_status(batch_id, "undone")

    # ── Duplicates ─────────────────────────────────────────

    def insert_duplicate(self, paper_id: str, duplicate_of: str, match_type: str, created_at: str) -> None:
        self.conn.execute(
            "INSERT INTO duplicates (paper_id, duplicate_of, match_type, created_at) VALUES (?,?,?,?)",
            (paper_id, duplicate_of, match_type, created_at),
        )
        self.conn.commit()

    # ── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _row_to_paper(row: sqlite3.Row) -> PaperRecord:
        return PaperRecord(
            id=row["id"],
            source_path=row["source_path"],
            current_path=row["current_path"],
            file_hash=row["file_hash"],
            title=row["title"],
            authors=json.loads(row["authors"]),
            first_author=row["first_author"],
            year=row["year"],
            venue=row["venue"],
            paper_type=row["paper_type"],
            doi=row["doi"],
            arxiv_id=row["arxiv_id"],
            confidence=row["confidence"],
            status=row["status"],
            evidence=json.loads(row["evidence"]),
        )

    def _fetch_single_paper(
        self,
        base_query: str,
        params: list[Any],
        *,
        include_statuses: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ) -> sqlite3.Row | None:
        query, filtered_params = self._apply_status_filters(
            base_query,
            params,
            include_statuses=include_statuses,
            exclude_statuses=exclude_statuses,
        )
        return self.conn.execute(query, filtered_params).fetchone()

    @staticmethod
    def _apply_status_filters(
        base_query: str,
        params: list[Any],
        *,
        include_statuses: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ) -> tuple[str, list[Any]]:
        query = base_query
        filtered_params = list(params)
        clauses: list[str] = []

        include = list(include_statuses or [])
        exclude = list(exclude_statuses or [])

        if include:
            placeholders = ",".join("?" for _ in include)
            clauses.append(f"status IN ({placeholders})")
            filtered_params.extend(include)

        if exclude:
            placeholders = ",".join("?" for _ in exclude)
            clauses.append(f"status NOT IN ({placeholders})")
            filtered_params.extend(exclude)

        if clauses:
            separator = " AND " if " WHERE " in base_query.upper() else " WHERE "
            query = f"{base_query}{separator}{' AND '.join(clauses)}"

        return query, filtered_params
