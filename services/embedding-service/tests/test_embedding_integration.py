"""Integration test for the Embedding Service pipeline.

Places an SQS2Message on SQS 2 and asserts:
  - SQS 3 messages appear with 768-dim float embeddings per chunk
  - documents.status = embedding in PostgreSQL

Requires docker-compose services: elasticmq, postgres.
Skipped automatically when infra env vars are not set.
"""

import asyncio
import json
import os
from unittest.mock import patch

import boto3
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.main import _process_message

from shared.models.chunk import ChunkMetadata
from shared.models.document import DocType
from shared.models.messages import SQS2Chunk, SQS2Message

pytestmark = pytest.mark.integration


def _infra_available() -> bool:
    return bool(
        os.getenv("DATABASE_URL")
        and os.getenv("SQS_QUEUE_2_URL")
        and os.getenv("SQS_QUEUE_3_URL")
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
class TestEmbeddingIntegration:
    DOC_ID = "embed-integ-doc-001"

    def _insert_document(self):
        db_url = os.getenv("DATABASE_URL", "")
        engine = create_async_engine(db_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async def _insert():
            async with session_factory() as session:
                await session.execute(
                    text("""
                        INSERT INTO documents (doc_id, job_id, title, doc_type, s3_key,
                            content_type, uploaded_by, target_index, status,
                            chunks_total, created_at, updated_at)
                        VALUES (:doc_id, gen_random_uuid(), 'Embedding Integration Test',
                            'clinical_guideline', 'raw-docs/embed-test.txt', 'text/plain',
                            'integration_test', 'live', 'processing', 2, NOW(), NOW())
                        ON CONFLICT (doc_id) DO NOTHING
                    """),
                    {"doc_id": self.DOC_ID},
                )
                await session.commit()

        asyncio.get_event_loop().run_until_complete(_insert())

    def test_sqs2_produces_sqs3_with_embeddings_and_pg_status(self, sqs):
        self._insert_document()

        meta = ChunkMetadata(
            doc_type=DocType.clinical_guideline,
            page_num=1,
            chunk_idx=0,
            version=1,
            target_index="live",
        )
        msg = SQS2Message(
            doc_id=self.DOC_ID,
            chunks=[
                SQS2Chunk(
                    chunk_id=f"{self.DOC_ID}_chunk_0000",
                    text="Aspirin 325mg once daily",
                    metadata=meta,
                ),
                SQS2Chunk(
                    chunk_id=f"{self.DOC_ID}_chunk_0001",
                    text="Metformin 500mg twice daily",
                    metadata=meta,
                ),
            ],
        )

        # Stub embed() to return deterministic 768-dim vectors (no real HF API needed)
        fake_vectors = [[float(i) / 1000] * 768 for i in range(len(msg.chunks))]

        async def fake_embed(texts: list[str]) -> list[list[float]]:
            return fake_vectors[: len(texts)]

        with patch("src.main._embedding_client") as mock_client:
            mock_client.embed = fake_embed
            asyncio.get_event_loop().run_until_complete(
                _process_message(msg.model_dump_json())
            )

        queue_3 = os.getenv("SQS_QUEUE_3_URL", "")
        response = sqs.receive_message(QueueUrl=queue_3, MaxNumberOfMessages=10)
        sqs3_messages = response.get("Messages", [])

        assert len(sqs3_messages) >= 2, "Expected at least 2 SQS 3 messages"
        for raw in sqs3_messages:
            body = json.loads(raw["Body"])
            assert body["doc_id"] == self.DOC_ID
            embedding = body["embedding"]
            assert isinstance(embedding, list)
            assert len(embedding) == 768
            assert all(isinstance(v, float) for v in embedding)

        # Verify PostgreSQL status updated to 'embedding'
        db_url = os.getenv("DATABASE_URL", "")
        engine = create_async_engine(db_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async def _check_status():
            async with session_factory() as session:
                result = await session.execute(
                    text("SELECT status FROM documents WHERE doc_id = :doc_id"),
                    {"doc_id": self.DOC_ID},
                )
                return result.fetchone()

        row = asyncio.get_event_loop().run_until_complete(_check_status())
        assert row is not None
        assert row[0] == "embedding"
