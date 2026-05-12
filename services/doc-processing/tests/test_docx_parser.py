"""Unit tests for the DOCX parser."""

from unittest.mock import MagicMock, patch

from src.parsers.docx_parser import parse


class TestDocxParser:
    def _make_mock_doc(self, paragraph_texts: list[str]) -> MagicMock:
        paragraphs = []
        for text in paragraph_texts:
            p = MagicMock()
            p.text = text
            paragraphs.append(p)
        doc = MagicMock()
        doc.paragraphs = paragraphs
        return doc

    def test_returns_single_page_tuple(self):
        mock_doc = self._make_mock_doc(["First paragraph.", "Second paragraph."])

        with patch("src.parsers.docx_parser.Document", return_value=mock_doc):
            result = parse(b"docx-bytes")

        assert len(result) == 1
        text, page_num = result[0]
        assert "First paragraph." in text
        assert "Second paragraph." in text

    def test_page_num_is_zero(self):
        mock_doc = self._make_mock_doc(["Some content."])
        with patch("src.parsers.docx_parser.Document", return_value=mock_doc):
            result = parse(b"docx-bytes")
        assert result[0][1] == 0

    def test_empty_paragraphs_excluded(self):
        mock_doc = self._make_mock_doc(["", "Real content.", "   "])
        with patch("src.parsers.docx_parser.Document", return_value=mock_doc):
            result = parse(b"docx-bytes")
        assert "Real content." in result[0][0]
        assert result[0][0].strip() == "Real content."

    def test_all_empty_returns_empty_list(self):
        mock_doc = self._make_mock_doc(["", "  "])
        with patch("src.parsers.docx_parser.Document", return_value=mock_doc):
            result = parse(b"docx-bytes")
        assert result == []
