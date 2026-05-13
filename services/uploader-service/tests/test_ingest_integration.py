"""Integration tests for POST /api/v1/knowledge/ingest.

Requires real MinIO and PostgreSQL (via docker-compose). Skip if not available.
Run with: pytest services/uploader-service/tests/test_ingest_integration.py -v

Environment variables needed:
  DATABASE_URL=postgresql+asyncpg://raghealth:raghealth_local@localhost:5432/raghealth
  S3_ENDPOINT_URL=http://localhost:9000
  S3_BUCKET=rag-health-local
  SQS_QUEUE_1_URL=http://localhost:9324/000000000000/doc-processing-queue
  AWS_ENDPOINT_URL=http://localhost:9324
"""

import io
import os

import boto3
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.main import app

pytestmark = pytest.mark.integration


def _infra_available() -> bool:
    db_url = os.getenv("DATABASE_URL", "")
    s3_url = os.getenv("S3_ENDPOINT_URL", "")
    return bool(db_url and s3_url)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def s3():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://localhost:9000"),
        aws_access_key_id=os.getenv("MINIO_ROOT_USER", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
        region_name="us-east-1",
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


@pytest.mark.skipif(not _infra_available(), reason="MinIO/PostgreSQL not available")
class TestIngestIntegration:
    def test_upload_creates_minio_object_pg_row_and_sqs_message(self, client, s3, sqs):
        bucket = os.getenv("S3_BUCKET", "rag-health-local")
        queue_url = os.getenv("SQS_QUEUE_1_URL", "http://localhost:9324/000000000000/doc-processing-queue")

        pdf_bytes = b"%PDF-1.4 integration test fixture"

        resp = client.post(
            "/api/v1/knowledge/ingest",
            data={
                "title": "Integration Test Doc",
                "doc_type": "hospital_policy",
                "uploaded_by": "integration_test",
                "target_index": "live",
            },
            files={"file": ("integration.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )

        assert resp.status_code == 202
        body = resp.json()
        doc_id = body["doc_id"]
        assert body["status"] == "pending"

        # Verify MinIO object exists
        prefix = f"raw-docs/{doc_id}/"
        objects = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        assert objects.get("KeyCount", 0) >= 1, f"No S3 object found under {prefix}"

        # Verify PostgreSQL row
        import asyncio
        db_url = os.getenv("DATABASE_URL", "")
        engine = create_async_engine(db_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async def _check_pg():
            async with session_factory() as session:
                result = await session.execute(
                    text("SELECT status FROM documents WHERE doc_id = :doc_id"),
                    {"doc_id": doc_id},
                )
                row = result.fetchone()
                return row

        row = asyncio.get_event_loop().run_until_complete(_check_pg())
        assert row is not None, f"No documents row for doc_id={doc_id}"
        assert row[0] == "pending"

        # Verify SQS 1 message count increased
        attrs = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessages"],
        )
        msg_count = int(attrs["Attributes"]["ApproximateNumberOfMessages"])
        assert msg_count >= 1, "Expected at least 1 message in SQS 1"
