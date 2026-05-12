"""Token-based text chunker using tiktoken (cl100k_base).

Produces overlapping chunks of at most MAX_TOKENS tokens with OVERLAP_TOKENS
tokens of context carried over between consecutive chunks.
"""

from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from shared.models.chunk import ChunkMetadata
from shared.models.document import DocType

_ENC = tiktoken.get_encoding("cl100k_base")

MAX_TOKENS: int = 512
OVERLAP_TOKENS: int = 50


@dataclass
class Chunk:
    text: str
    token_count: int
    metadata: ChunkMetadata


def chunk_pages(
    pages: list[tuple[str, int]],
    doc_id: str,
    doc_type: DocType,
    target_index: str = "live",
    max_tokens: int = MAX_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    """Split *pages* into overlapping token chunks.

    Args:
        pages: Output of a parser — list of ``(text, page_num)`` tuples.
        doc_id: Parent document identifier (used to derive chunk IDs upstream).
        doc_type: Clinical document category.
        target_index: Weaviate index alias to write into.
        max_tokens: Maximum tokens per chunk (inclusive).
        overlap_tokens: Number of tokens carried over from the previous chunk.

    Returns:
        Ordered list of :class:`Chunk` objects.
    """
    chunks: list[Chunk] = []
    chunk_idx = 0

    for text, page_num in pages:
        token_ids = _ENC.encode(text)
        pos = 0

        while pos < len(token_ids):
            window = token_ids[pos : pos + max_tokens]
            chunk_text = _ENC.decode(window)
            chunks.append(
                Chunk(
                    text=chunk_text,
                    token_count=len(window),
                    metadata=ChunkMetadata(
                        doc_type=doc_type,
                        page_num=page_num,
                        chunk_idx=chunk_idx,
                        version=1,
                        target_index=target_index,
                    ),
                )
            )
            chunk_idx += 1
            # Advance by (max_tokens - overlap) so the next chunk shares
            # overlap_tokens tokens with the current one.
            step = max_tokens - overlap_tokens
            pos += step

    return chunks
