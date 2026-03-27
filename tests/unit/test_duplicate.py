"""Tests for duplicate detection."""

import pytest

from tidypaper.core.duplicate import check_duplicate
from tidypaper.db.database import Database
from tidypaper.models.paper import PaperRecord


@pytest.fixture
def db(tmp_path):
    """Create a temporary database for testing."""
    database = Database(tmp_path / "test.db")
    database.connect()
    yield database
    database.close()


class TestCheckDuplicate:
    """Test four-layer duplicate detection."""

    def _make_paper(self, **kwargs) -> PaperRecord:
        from uuid import uuid4
        defaults = {
            "id": str(uuid4()),
            "file_hash": "abc123",
            "title": "Test Paper",
            "source_path": "/test/paper.pdf",
            "current_path": "/test/paper.pdf",
        }
        defaults.update(kwargs)
        return PaperRecord(**defaults)

    def test_hash_duplicate(self, db):
        existing = self._make_paper(file_hash="same_hash")
        db.insert_paper(existing)

        new = self._make_paper(file_hash="same_hash")
        result = check_duplicate(new, db)
        assert result.is_duplicate
        assert result.match_type == "hash"

    def test_doi_duplicate(self, db):
        existing = self._make_paper(file_hash="hash1", doi="10.1234/test")
        db.insert_paper(existing)

        new = self._make_paper(file_hash="hash2", doi="10.1234/test")
        result = check_duplicate(new, db)
        assert result.is_duplicate
        assert result.match_type == "doi"

    def test_arxiv_duplicate(self, db):
        existing = self._make_paper(file_hash="hash1", arxiv_id="2301.12345")
        db.insert_paper(existing)

        new = self._make_paper(file_hash="hash2", arxiv_id="2301.12345")
        result = check_duplicate(new, db)
        assert result.is_duplicate
        assert result.match_type == "arxiv_id"

    def test_title_duplicate(self, db):
        existing = self._make_paper(
            file_hash="hash1",
            title="Attention Is All You Need",
        )
        db.insert_paper(existing)

        new = self._make_paper(
            file_hash="hash2",
            title="Attention Is All You Need",
        )
        result = check_duplicate(new, db)
        assert result.is_duplicate
        assert result.match_type == "title"

    def test_no_duplicate(self, db):
        existing = self._make_paper(
            file_hash="hash1",
            title="Paper A",
            doi="10.1234/a",
        )
        db.insert_paper(existing)

        new = self._make_paper(
            file_hash="hash2",
            title="Completely Different Paper B",
            doi="10.1234/b",
        )
        result = check_duplicate(new, db)
        assert not result.is_duplicate

    def test_empty_database(self, db):
        paper = self._make_paper()
        result = check_duplicate(paper, db)
        assert not result.is_duplicate

    def test_preview_records_are_ignored(self, db):
        preview = self._make_paper(file_hash="same_hash", status="preview")
        db.insert_paper(preview)

        new = self._make_paper(file_hash="same_hash")
        result = check_duplicate(new, db)
        assert not result.is_duplicate
