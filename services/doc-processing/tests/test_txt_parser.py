"""Unit tests for the TXT parser (UTF-8 and latin-1 fixtures)."""

from src.parsers.txt_parser import parse


class TestTxtParser:
    def test_utf8_text_parsed(self):
        content = "Clinical guideline: administer 5 mg aspirin daily."
        result = parse(content.encode("utf-8"))
        assert len(result) == 1
        assert result[0][0] == content
        assert result[0][1] == 1

    def test_latin1_fallback(self):
        # é is 0xe9 in latin-1 but invalid in UTF-8 without the right sequence
        content_latin1 = "Maladie cœliaque – résumé".encode("latin-1")
        result = parse(content_latin1)
        assert len(result) == 1
        assert result[0][1] == 1
        # Text must contain something (decoded without error)
        assert len(result[0][0]) > 0

    def test_empty_bytes_returns_empty_list(self):
        assert parse(b"") == []

    def test_whitespace_only_returns_empty_list(self):
        assert parse(b"   \n\t  ") == []

    def test_page_num_always_one(self):
        result = parse(b"Any content")
        assert result[0][1] == 1

    def test_multi_line_preserved(self):
        lines = "Line one\nLine two\nLine three"
        result = parse(lines.encode("utf-8"))
        assert "Line one" in result[0][0]
        assert "Line three" in result[0][0]
