"""Integration test for the Doc Processing pipeline.

Places a DocProcessingJob message on SQS 1 and asserts:
  - SQS 2 messages appear (≥1 chunk)
  - documents.status = processing in PostgreSQL
  - Chunk text contains no raw PII test strings

Requires docker-compose services: elasticmq, minio, postgres.
Skipped automatically when infra env vars are not set.
"""

import asyncio
import json
import os
import time
from unittest.mock import patch

import boto3
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.models.document import DocType
from shared.models.messages import SQS1Message
from src.main import _process_message

pytestmark = pytest.mark.integration


def _infra_available() -> bool:
    return bool(
        os.getenv("DATABASE_URL")
        and os.getenv("SQS_QUEUE_1_URL")
        and os.getenv("SQS_QUEUE_2_URL")
        and os.getenv("S3_ENDPOINT_URL")
    )


@pytest.fixture(scope="module")
def sqs():
    return boto3.client(
        "sqs",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://localhost:9324"),
        region_name="us-east-1",
        aws_access_key_id="x",
        aws_secret_access_key="x",
    )


@pytest.mark.skipif(not _infra_available(), reason="Infrastructure not available")
class TestDocProcessingIntegration:
    PII_TEXT = b"Patient John Smith (SSN: 123-45-6789) admitted on 2024-01-15."
    TXT_CONTENT_TYPE = "text/plain"

    def test_sqs1_message_produces_sqs2_chunks_and_pg_update(self, sqs):
        doc_id = "integ-test-doc-001"
        s3_key = f"raw-docs/{doc_id}/test.txt"
        queue_2 = os.getenv("SQS_QUEUE_2_URL", "")

        # Pre-insert document row
        db_url = os.getenv("DATABASE_URL", "")
        engine = create_async_engine(db_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async def _insert():
            async with session_factory() as session:
                await session.execute(
                    text("""
                        INSERT INTO documents (doc_id, job_id, title, doc_type, s3_key,
                            content_type, uploaded_by, target_index, status, created_at, updated_at)
                        VALUES (:doc_id, gen_random_uuid(), 'Integration Test', 'other',
                            :s3_key, :ct, 'test', 'live', 'pending', NOW(), NOW())
                        ON CONFLICT (doc_id) DO NOTHING
                    """),
                    {"doc_id": doc_id, "s3_key": s3_key, "ct": self.TXT_CONTENT_TYPE},
                )
                await session.commit()

        asyncio.get_event_loop().run_until_complete(_insert())

        msg = SQS1Message(
            doc_id=doc_id,
            s3_key=s3_key,
            content_type=self.TXT_CONTENT_TYPE,
            uploaded_by="integration_test",
            target_index="live",
            job_id="integ-job-001",
            uploaded_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )

        # Mock S3 download to return PII text
        from unittest.mock import AsyncMock
        with patch("src.main._s3") as mock_s3:
            mock_s3.download = AsyncMock(return_value=self.PII_TEXT)
            asyncio.get_event_loop().run_until_complete(
                _process_message(msg.model_dump_json())
            )

        # Verify SQS 2 has messages
        attrs = sqs.get_queue_attributes(
            QueueUrl=queue_2,
            AttributeNames=["ApproximateNumberOfMessages"],
        )
        assert int(attrs["Attributes"]["ApproximateNumberOfMessages"]) >= 1

        # Receive and inspect one chunk message
        response = sqs.receive_message(QueueUrl=queue_2, MaxNumberOfMessages=1)
        messages = response.get("Messages", [])
        assert messages, "No SQS 2 messages received"
        body = json.loads(messages[0]["Body"])
        assert body["doc_id"] == doc_id
        assert body["chunks"]
        # PII must not appear raw in any chunk
        for chunk in body["chunks"]:
            assert "John Smith" not in chunk["text"]
            assert "123-45-6789" not in chunk["text"]

        # Verify PG status
        async def _check_pg():
            async with session_factory() as session:
                result = await session.execute(
                    text("SELECT status FROM documents WHERE doc_id = :doc_id"),
                    {"doc_id": doc_id},
                )
                return result.fetchone()

        row = asyncio.get_event_loop().run_until_complete(_check_pg())
        assert row is not None
        assert row[0] == "processing"
