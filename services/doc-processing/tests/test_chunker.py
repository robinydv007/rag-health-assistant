"""Unit tests for the token-based chunker.

Verifies chunk sizes, overlap, and ChunkMetadata field correctness.
tiktoken is a pure-Python library with no external model downloads needed.
"""

import tiktoken
from src.chunker import MAX_TOKENS, OVERLAP_TOKENS, chunk_pages

from shared.models.document import DocType

_ENC: tiktoken.Encoding | None = None


def _enc() -> tiktoken.Encoding:
    global _ENC
    if _ENC is None:
        _ENC = tiktoken.get_encoding("cl100k_base")
    return _ENC


def _make_long_text(token_count: int) -> str:
    word = "clinical "
    tokens_per_word = len(_enc().encode(word))
    words_needed = token_count // tokens_per_word + 1
    return (word * words_needed).strip()


class TestChunkerSizes:
    def test_single_short_page_produces_one_chunk(self):
        pages = [("short text", 1)]
        chunks = chunk_pages(pages, doc_id="d1", doc_type=DocType.other)
        assert len(chunks) == 1
        assert chunks[0].token_count <= MAX_TOKENS

    def test_long_text_produces_multiple_chunks(self):
        long_text = _make_long_text(1100)  # ~2 full chunks
        pages = [(long_text, 1)]
        chunks = chunk_pages(pages, doc_id="d1", doc_type=DocType.other)
        assert len(chunks) >= 2

    def test_all_chunks_within_max_token_limit(self):
        long_text = _make_long_text(2000)
        pages = [(long_text, 1)]
        chunks = chunk_pages(pages, doc_id="d1", doc_type=DocType.other)
        for c in chunks:
            assert c.token_count <= MAX_TOKENS, (
                f"chunk {c.metadata.chunk_idx} has {c.token_count} tokens (max {MAX_TOKENS})"
            )

    def test_adjacent_chunks_share_overlap_tokens(self):
        long_text = _make_long_text(1100)
        pages = [(long_text, 1)]
        chunks = chunk_pages(pages, doc_id="d1", doc_type=DocType.other)
        assert len(chunks) >= 2
        toks0 = _enc().encode(chunks[0].text)
        toks1 = _enc().encode(chunks[1].text)
        # The last OVERLAP_TOKENS of chunk 0 should equal first OVERLAP_TOKENS of chunk 1
        overlap = min(OVERLAP_TOKENS, len(toks0), len(toks1))
        assert toks0[-overlap:] == toks1[:overlap]


class TestChunkerMetadata:
    def test_chunk_idx_is_sequential(self):
        long_text = _make_long_text(1100)
        pages = [(long_text, 1)]
        chunks = chunk_pages(pages, doc_id="d1", doc_type=DocType.clinical_guideline)
        for i, c in enumerate(chunks):
            assert c.metadata.chunk_idx == i

    def test_page_num_propagated_correctly(self):
        pages = [("page one text", 3), ("page two text", 7)]
        chunks = chunk_pages(pages, doc_id="d1", doc_type=DocType.hospital_policy)
        assert chunks[0].metadata.page_num == 3
        assert chunks[1].metadata.page_num == 7

    def test_doc_type_propagated(self):
        pages = [("some clinical text", 1)]
        chunks = chunk_pages(
            pages, doc_id="d1", doc_type=DocType.drug_formulary, target_index="shadow"
        )
        assert chunks[0].metadata.doc_type == DocType.drug_formulary
        assert chunks[0].metadata.target_index == "shadow"

    def test_version_is_one(self):
        pages = [("text content", 1)]
        chunks = chunk_pages(pages, doc_id="d1", doc_type=DocType.other)
        assert all(c.metadata.version == 1 for c in chunks)

    def test_empty_pages_produce_no_chunks(self):
        chunks = chunk_pages([], doc_id="d1", doc_type=DocType.other)
        assert chunks == []
