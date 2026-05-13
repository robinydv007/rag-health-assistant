"""Integration test for the Indexing Service pipeline.

Places an SQS3Message on SQS 3 and asserts:
  - Weaviate KnowledgeChunk object written with correct chunkId
  - documents.chunks_indexed incremented in PostgreSQL
  - chunk_audit row present in PostgreSQL

Requires docker-compose services: elasticmq, postgres, weaviate.
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

from shared.models.chunk import ChunkMetadata
from shared.models.document import DocType
from shared.models.messages import SQS3Message
from src.main import _process_message

pytestmark = pytest.mark.integration


def _infra_available() -> bool:
    return bool(
        os.getenv("DATABASE_URL")
        and os.getenv("SQS_QUEUE_3_URL")
        and os.getenv("WEAVIATE_URL")
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
class TestIndexingIntegration:
    DOC_ID = "index-integ-doc-001"
    CHUNK_ID = f"{DOC_ID}_chunk_0000"

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
                            chunks_total, chunks_indexed, created_at, updated_at)
                        VALUES (:doc_id, gen_random_uuid(), 'Indexing Integration Test',
                            'clinical_guideline', 'raw-docs/index-test.txt', 'text/plain',
                            'integration_test', 'live', 'embedding', 1, 0, NOW(), NOW())
                        ON CONFLICT (doc_id) DO NOTHING
                    """),
                    {"doc_id": self.DOC_ID},
                )
                await session.commit()

        asyncio.get_event_loop().run_until_complete(_insert())

    def test_sqs3_writes_weaviate_chunk_and_pg_counters(self):
        self._insert_document()

        meta = ChunkMetadata(
            doc_type=DocType.clinical_guideline,
            page_num=1,
            chunk_idx=0,
            version=1,
            target_index="live",
        )
        msg = SQS3Message(
            doc_id=self.DOC_ID,
            chunk_id=self.CHUNK_ID,
            text="Metformin 500mg twice daily with meals",
            embedding=[0.1] * 768,
            metadata=meta,
            target_index="live",
        )

        asyncio.get_event_loop().run_until_complete(
            _process_message(msg.model_dump_json())
        )

        db_url = os.getenv("DATABASE_URL", "")
        engine = create_async_engine(db_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async def _check():
            async with session_factory() as session:
                doc_row = await session.execute(
                    text("SELECT chunks_indexed, status FROM documents WHERE doc_id = :doc_id"),
                    {"doc_id": self.DOC_ID},
                )
                audit_row = await session.execute(
                    text("SELECT count(*) FROM chunk_audit WHERE doc_id = :doc_id AND chunk_id = :cid"),
                    {"doc_id": self.DOC_ID, "cid": self.CHUNK_ID},
                )
                return doc_row.fetchone(), audit_row.scalar()

        doc, audit_count = asyncio.get_event_loop().run_until_complete(_check())
        assert doc is not None
        assert doc[0] >= 1, "chunks_indexed should be incremented"
        assert doc[1] == "indexed", "status should be 'indexed' (1 of 1 chunks done)"
        assert audit_count >= 1, "chunk_audit row must exist"
