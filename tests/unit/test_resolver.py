"""Tests for DOI and arXiv ID extraction."""

import pytest

from tidypaper.core.resolver import extract_arxiv_id, extract_doi, extract_venue_hints


class TestExtractDoi:
    """Test DOI extraction from text."""

    def test_standard_doi(self):
        text = "doi: 10.1038/s41586-021-03819-2"
        assert extract_doi(text) == "10.1038/s41586-021-03819-2"

    def test_doi_in_url(self):
        text = "https://doi.org/10.1145/3394486.3403305"
        assert extract_doi(text) == "10.1145/3394486.3403305"

    def test_doi_in_pdf_text(self):
        text = "Published under DOI 10.5555/3454287.3454581 by the conference."
        assert extract_doi(text) == "10.5555/3454287.3454581"

    def test_no_doi(self):
        assert extract_doi("This is a regular text with no DOI.") is None

    def test_empty_string(self):
        assert extract_doi("") is None

    def test_strips_trailing_dot(self):
        text = "DOI: 10.1234/test.doi."
        result = extract_doi(text)
        assert result is not None
        assert not result.endswith(".")


class TestExtractArxivId:
    """Test arXiv ID extraction."""

    def test_new_style(self):
        text = "arXiv:2301.12345"
        assert extract_arxiv_id(text) == "2301.12345"

    def test_new_style_with_version(self):
        text = "arXiv:2301.12345v2"
        assert extract_arxiv_id(text) == "2301.12345v2"

    def test_from_url(self):
        text = "https://arxiv.org/abs/2301.12345"
        assert extract_arxiv_id(text) == "2301.12345"

    def test_from_pdf_url(self):
        text = "https://arxiv.org/pdf/2301.12345"
        assert extract_arxiv_id(text) == "2301.12345"

    def test_no_arxiv(self):
        assert extract_arxiv_id("Regular text") is None

    def test_from_filename(self):
        assert extract_arxiv_id("", filename="2301.12345v1.pdf") is None
        assert extract_arxiv_id("arXiv paper", filename="2301.12345v1.pdf") == "2301.12345v1"


class TestExtractVenueHints:
    """Test venue hint extraction."""

    def test_known_venues(self):
        text = "Published at NeurIPS 2024"
        hints = extract_venue_hints(text)
        assert "NeurIPS" in hints

    def test_proceedings_pattern(self):
        text = "In Proceedings of the 38th AAAI Conference on AI."
        hints = extract_venue_hints(text)
        assert any("AAAI" in h for h in hints)

    def test_multiple_venues(self):
        text = "CVPR and ICCV papers are popular."
        hints = extract_venue_hints(text)
        assert "CVPR" in hints
        assert "ICCV" in hints

    def test_no_venue(self):
        hints = extract_venue_hints("This is about machine learning.")
        assert len(hints) == 0
