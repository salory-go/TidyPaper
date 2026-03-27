"""Tests for filename generation from paper metadata."""

import pytest

from tidypaper.core.naming import generate_filename
from tidypaper.models.paper import PaperRecord


class TestGenerateFilename:
    """Test filename generation with various metadata states."""

    def _make_paper(self, **kwargs) -> PaperRecord:
        defaults = {
            "title": "Attention Is All You Need",
            "year": 2017,
            "venue": "NeurIPS",
            "first_author": "Ashish Vaswani",
        }
        defaults.update(kwargs)
        return PaperRecord(**defaults)

    def test_default_template(self):
        paper = self._make_paper()
        result = generate_filename(paper)
        assert result == "2017 - NeurIPS - Attention Is All You Need.pdf"

    def test_missing_venue(self):
        paper = self._make_paper(venue="")
        result = generate_filename(paper)
        # "Unknown" segments should be stripped
        assert "Unknown" not in result
        assert "2017 - Attention Is All You Need.pdf" == result

    def test_missing_year(self):
        paper = self._make_paper(year=None)
        result = generate_filename(paper)
        assert "Unknown" not in result
        assert "NeurIPS - Attention Is All You Need.pdf" == result

    def test_all_missing(self):
        paper = PaperRecord(title="Untitled")
        result = generate_filename(paper)
        assert result == "Untitled.pdf"

    def test_custom_template(self):
        paper = self._make_paper()
        result = generate_filename(paper, "{first_author} et al. - {year} - {title}")
        assert result == "Ashish Vaswani et al. - 2017 - Attention Is All You Need.pdf"

    def test_illegal_chars_in_title(self):
        paper = self._make_paper(title='GPT-4: A "Large" Model')
        result = generate_filename(paper)
        assert ":" not in result
        assert '"' not in result
        assert result.endswith(".pdf")

    def test_very_long_title(self):
        paper = self._make_paper(title="A" * 300)
        result = generate_filename(paper)
        assert len(result) <= 210  # 200 + ".pdf"
