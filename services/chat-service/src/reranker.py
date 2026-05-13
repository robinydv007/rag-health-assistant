"""Score-based reranker.

Sorts search results by their hybrid score (descending) and returns the top-N.
In Phase 1 this is a simple sort; Phase 3 may add cross-encoder reranking.
"""

from __future__ import annotations

from .models import SearchResult

_DEFAULT_TOP_N = 3


def rerank(results: list[SearchResult], top_n: int = _DEFAULT_TOP_N) -> list[SearchResult]:
    """Return the top-N results sorted by descending hybrid score.

    Args:
        results: Candidate results from :func:`searcher.hybrid_search`.
        top_n: Number of results to return.

    Returns:
        Up to *top_n* results with the highest scores.
    """
    return sorted(results, key=lambda r: r.score, reverse=True)[:top_n]
