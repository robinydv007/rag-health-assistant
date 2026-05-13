"""Plain-text parser with UTF-8 / latin-1 fallback.

Returns a single page (page_num=1) containing the full file text.
"""

from __future__ import annotations


def parse(data: bytes) -> list[tuple[str, int]]:
    """Decode *data* and return it as a single page.

    Tries UTF-8 first; falls back to latin-1 if decoding fails (latin-1
    never raises on arbitrary byte sequences).

    Args:
        data: Raw file content.

    Returns:
        ``[(text, 1)]`` or empty list if the file has no printable content.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")

    return [(text, 1)] if text.strip() else []
