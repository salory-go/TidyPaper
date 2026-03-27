"""Tests for filename sanitization utilities."""

import pytest

from tidypaper.utils.filename import sanitize_filename


class TestSanitizeFilename:
    """Test cross-platform filename sanitization."""

    def test_removes_windows_illegal_chars(self):
        assert sanitize_filename('hello<world>test') == "hello world test"
        assert sanitize_filename('a:b|c?d') == "a b c d"

    def test_collapses_consecutive_spaces(self):
        assert sanitize_filename("hello   world") == "hello world"

    def test_collapses_consecutive_dots(self):
        assert sanitize_filename("file...name") == "file.name"

    def test_strips_leading_trailing_dots_and_spaces(self):
        assert sanitize_filename("  .hello. ") == "hello"
        assert sanitize_filename("...test...") == "test"

    def test_truncates_long_names(self):
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200

    def test_empty_string_returns_untitled(self):
        assert sanitize_filename("") == "Untitled"

    def test_only_illegal_chars_returns_untitled(self):
        assert sanitize_filename('???***') == "Untitled"

    def test_normal_academic_title(self):
        title = "Attention Is All You Need"
        assert sanitize_filename(title) == title

    def test_title_with_colon(self):
        result = sanitize_filename("GPT-4: A Large Language Model")
        assert ":" not in result
        assert "GPT-4" in result

    def test_preserves_hyphens_and_parentheses(self):
        result = sanitize_filename("Self-Supervised (2024)")
        assert result == "Self-Supervised (2024)"
