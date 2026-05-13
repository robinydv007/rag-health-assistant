"""PDF parser using pdfplumber.

Returns a list of (text, page_num) tuples, one per page that has extractable
text. Pages with no text (e.g. image-only scans) are silently skipped.
"""

from __future__ import annotations

import io

import pdfplumber


def parse(data: bytes) -> list[tuple[str, int]]:
    """Extract text from *data* (raw PDF bytes).

    Args:
        data: Raw PDF file content.

    Returns:
        List of ``(page_text, page_num)`` tuples. ``page_num`` is 1-indexed.
        Empty list if no text could be extracted.
    """
    pages: list[tuple[str, int]] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((text, page_num))
    return pages
