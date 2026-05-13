"""Unit tests for WeaviateWriter — mocks weaviate client."""

import pytest
from unittest.mock import MagicMock, patch

from shared.models.chunk import ChunkMetadata
from shared.models.document import DocType
from shared.models.messages import SQS3Message
from src.weaviate_writer import WeaviateWriter, EMBEDDED_MODEL, _chunk_uuid

_MSG = SQS3Message(
    doc_id="doc-abc",
    chunk_id="doc-abc_chunk_0000",
    text="Aspirin 325mg once daily for pain relief",
    embedding=[0.1] * 768,
    metadata=ChunkMetadata(
        doc_type=DocType.clinical_guideline,
        page_num=3,
        chunk_idx=0,
        version=1,
        target_index="live",
    ),
    target_index="live",
)


def _make_mock_client():
    mock_collection = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.collections.get.return_value = mock_collection
    return mock_client, mock_collection


def test_weaviate_writer_inserts_with_correct_properties():
    """WeaviateWriter inserts all required properties and vector."""
    mock_client, mock_collection = _make_mock_client()

    with patch("src.weaviate_writer._make_client", return_value=mock_client):
        writer = WeaviateWriter(weaviate_url="http://weaviate:8080")
        writer.upsert(_MSG, title="Clinical Guideline Test")

    mock_collection.data.insert.assert_called_once()
    call_kwargs = mock_collection.data.insert.call_args.kwargs
    props = call_kwargs["properties"]

    assert props["docId"] == "doc-abc"
    assert props["chunkId"] == "doc-abc_chunk_0000"
    assert props["chunkIdx"] == 0
    assert props["text"] == _MSG.text
    assert props["docType"] == "clinical_guideline"
    assert props["title"] == "Clinical Guideline Test"
    assert props["pageNum"] == 3
    assert props["embeddedModel"] == EMBEDDED_MODEL
    assert "indexedAt" in props


def test_weaviate_writer_vector_is_correct_length():
    """WeaviateWriter passes the embedding vector with correct length."""
    mock_client, mock_collection = _make_mock_client()

    with patch("src.weaviate_writer._make_client", return_value=mock_client):
        writer = WeaviateWriter(weaviate_url="http://weaviate:8080")
        writer.upsert(_MSG)

    call_kwargs = mock_collection.data.insert.call_args.kwargs
    assert len(call_kwargs["vector"]) == 768


def test_weaviate_writer_uses_deterministic_uuid():
    """WeaviateWriter uses a deterministic UUID derived from chunk_id."""
    mock_client, mock_collection = _make_mock_client()

    with patch("src.weaviate_writer._make_client", return_value=mock_client):
        writer = WeaviateWriter(weaviate_url="http://weaviate:8080")
        writer.upsert(_MSG)

    call_kwargs = mock_collection.data.insert.call_args.kwargs
    expected_uuid = _chunk_uuid(_MSG.chunk_id)
    assert call_kwargs["uuid"] == expected_uuid


def test_weaviate_writer_replaces_on_duplicate():
    """WeaviateWriter falls back to replace() when UUID already exists."""
    mock_client, mock_collection = _make_mock_client()
    mock_collection.data.insert.side_effect = Exception("already exists: 422")

    with patch("src.weaviate_writer._make_client", return_value=mock_client):
        writer = WeaviateWriter(weaviate_url="http://weaviate:8080")
        writer.upsert(_MSG)

    mock_collection.data.replace.assert_called_once()
