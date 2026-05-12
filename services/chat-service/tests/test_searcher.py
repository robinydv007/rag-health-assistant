"""Unit tests for the Weaviate hybrid searcher.

Weaviate client is mocked — these tests verify the query construction
and result mapping logic without requiring a live Weaviate instance.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.searcher import SearchResult, hybrid_search, _ALPHA, _ZERO_VECTOR


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_mock_weaviate_object(doc_id: str, text: str, title: str, page: int, score: float):
    obj = MagicMock()
    obj.properties = {
        "docId": doc_id,
        "chunkId": f"{doc_id}_chunk_0000",
        "text": text,
        "title": title,
        "pageNum": page,
    }
    obj.metadata = MagicMock()
    obj.metadata.score = score
    return obj


def _make_mock_client(objects: list) -> MagicMock:
    mock_collection = MagicMock()
    mock_response = MagicMock()
    mock_response.objects = objects
    mock_collection.query.hybrid.return_value = mock_response

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.collections.get.return_value = mock_collection
    return mock_client


@pytest.fixture()
def two_objects():
    return [
        _make_mock_weaviate_object("d1", "Aspirin 81mg for cardiovascular", "Formulary", 3, 0.9),
        _make_mock_weaviate_object("d2", "Heparin dosing protocol", "Guidelines", 7, 0.6),
    ]


class TestHybridSearch:
    def test_returns_list_of_search_results(self, two_objects):
        mock_client = _make_mock_client(two_objects)
        with patch("src.searcher._make_client", return_value=mock_client):
            results = _run(hybrid_search("aspirin dosing", []))
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

    def test_zero_vector_used(self, two_objects):
        mock_client = _make_mock_client(two_objects)
        with patch("src.searcher._make_client", return_value=mock_client):
            _run(hybrid_search("query", []))
        collection = mock_client.collections.get.return_value
        call_kwargs = collection.query.hybrid.call_args.kwargs
        assert call_kwargs["vector"] == _ZERO_VECTOR
        assert call_kwargs["alpha"] == _ALPHA

    def test_synonym_terms_appended_to_query(self, two_objects):
        mock_client = _make_mock_client(two_objects)
        with patch("src.searcher._make_client", return_value=mock_client):
            _run(hybrid_search("MI", ["myocardial infarction", "heart attack"]))
        collection = mock_client.collections.get.return_value
        query_str = collection.query.hybrid.call_args.kwargs["query"]
        assert "MI" in query_str
        assert "myocardial infarction" in query_str
        assert "heart attack" in query_str

    def test_score_mapped_from_metadata(self, two_objects):
        mock_client = _make_mock_client(two_objects)
        with patch("src.searcher._make_client", return_value=mock_client):
            results = _run(hybrid_search("query", []))
        assert results[0].score == pytest.approx(0.9)
        assert results[1].score == pytest.approx(0.6)

    def test_empty_results(self):
        mock_client = _make_mock_client([])
        with patch("src.searcher._make_client", return_value=mock_client):
            results = _run(hybrid_search("unknown query", []))
        assert results == []
