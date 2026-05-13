"""Unit tests for SQS3Publisher — verifies IndexingJob schema compliance."""

from unittest.mock import MagicMock, patch

import pytest
from src.publisher import SQS3Publisher

from shared.models.chunk import ChunkMetadata
from shared.models.document import DocType
from shared.models.messages import SQS3Message

_EMBEDDING = [0.1] * 3072
_META = ChunkMetadata(
    doc_type=DocType.clinical_guideline,
    page_num=1,
    chunk_idx=0,
    version=1,
    target_index="live",
)


@pytest.mark.asyncio
async def test_publisher_sends_indexing_job_schema():
    """SQS3Publisher sends a message that deserializes to a valid SQS3Message."""
    sent: list[dict] = []

    def fake_send(**kwargs):
        sent.append({"QueueUrl": kwargs["QueueUrl"], "body": kwargs["MessageBody"]})

    with patch("src.publisher.boto3") as mock_boto3:
        mock_sqs = MagicMock()
        mock_sqs.send_message.side_effect = fake_send
        mock_boto3.client.return_value = mock_sqs

        publisher = SQS3Publisher(
            queue_url="http://fake:9324/000000000000/indexing-queue",
            region="us-east-1",
        )
        await publisher.publish(
            doc_id="doc-123",
            chunk_id="doc-123_chunk_0000",
            text="Aspirin 325mg once daily for pain relief",
            embedding=_EMBEDDING,
            metadata=_META,
        )

    assert len(sent) == 1
    body = SQS3Message.model_validate_json(sent[0]["body"])
    assert body.doc_id == "doc-123"
    assert body.chunk_id == "doc-123_chunk_0000"
    assert body.text == "Aspirin 325mg once daily for pain relief"
    assert len(body.embedding) == 3072
    assert body.target_index == "live"
    assert body.metadata.doc_type == DocType.clinical_guideline
