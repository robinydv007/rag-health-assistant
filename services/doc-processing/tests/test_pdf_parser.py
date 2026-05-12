"""Unit tests for the PDF parser.

Uses a minimal in-memory PDF fixture built with reportlab (if available)
or a raw-bytes fixture to avoid heavy file fixtures on disk.
"""

import io
from unittest.mock import MagicMock, patch

import pytest

from src.parsers.pdf_parser import parse


class TestPdfParser:
    def test_returns_list_of_page_tuples(self):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Patient presents with chest pain."

        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        with patch("src.parsers.pdf_parser.pdfplumber.open", return_value=mock_pdf):
            result = parse(b"%PDF-1.4 fixture")

        assert len(result) == 1
        text, page_num = result[0]
        assert "chest pain" in text
        assert page_num == 1

    def test_page_num_is_1_indexed(self):
        pages = [MagicMock(), MagicMock()]
        pages[0].extract_text.return_value = "Page one content"
        pages[1].extract_text.return_value = "Page two content"

        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = pages

        with patch("src.parsers.pdf_parser.pdfplumber.open", return_value=mock_pdf):
            result = parse(b"%PDF fixture")

        assert result[0][1] == 1
        assert result[1][1] == 2

    def test_empty_pages_skipped(self):
        pages = [MagicMock(), MagicMock()]
        pages[0].extract_text.return_value = ""          # empty → skip
        pages[1].extract_text.return_value = "Real text"

        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = pages

        with patch("src.parsers.pdf_parser.pdfplumber.open", return_value=mock_pdf):
            result = parse(b"%PDF fixture")

        assert len(result) == 1
        assert result[0][1] == 2  # Page 2, the non-empty one

    def test_none_extract_text_handled(self):
        page = MagicMock()
        page.extract_text.return_value = None

        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [page]

        with patch("src.parsers.pdf_parser.pdfplumber.open", return_value=mock_pdf):
            result = parse(b"%PDF fixture")

        assert result == []
