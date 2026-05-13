"""DOCX parser using python-docx.

DOCX files have no reliable page boundary information at the paragraph level,
so all text is returned as a single page (page_num=0).
"""

from __future__ import annotations

import io

from docx import Document


def parse(data: bytes) -> list[tuple[str, int]]:
    """Extract text from *data* (raw DOCX bytes).

    Args:
        data: Raw DOCX file content.

    Returns:
        A single-element list ``[(full_text, 0)]``, or empty if no text found.
        page_num is set to 0 to indicate DOCX has no page concept.
    """
    doc = Document(io.BytesIO(data))
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [(text, 0)] if text else []
