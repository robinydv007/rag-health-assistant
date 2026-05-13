"""Unit tests for the score-based reranker."""

from src.models import SearchResult
from src.reranker import rerank


def _make_result(doc_id: str, score: float) -> SearchResult:
    return SearchResult(
        doc_id=doc_id, chunk_id=f"{doc_id}_c0",
        text="text", title="Title", page_num=1, score=score,
    )


class TestReranker:
    def test_returns_top_3_by_score(self):
        results = [
            _make_result("d1", 0.3),
            _make_result("d2", 0.9),
            _make_result("d3", 0.7),
            _make_result("d4", 0.1),
            _make_result("d5", 0.5),
        ]
        top = rerank(results)
        assert len(top) == 3
        assert top[0].doc_id == "d2"
        assert top[1].doc_id == "d3"
        assert top[2].doc_id == "d5"

    def test_scores_descending(self):
        results = [_make_result(f"d{i}", float(i) / 10) for i in range(10)]
        top = rerank(results)
        scores = [r.score for r in top]
        assert scores == sorted(scores, reverse=True)

    def test_fewer_than_top_n_returns_all(self):
        results = [_make_result("d1", 0.9), _make_result("d2", 0.5)]
        top = rerank(results)
        assert len(top) == 2

    def test_empty_input_returns_empty(self):
        assert rerank([]) == []

    def test_custom_top_n(self):
        results = [_make_result(f"d{i}", float(i)) for i in range(10)]
        top = rerank(results, top_n=5)
        assert len(top) == 5
