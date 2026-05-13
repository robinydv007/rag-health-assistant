"""Indexing Service — SQS 3 consumer: write vectors to Weaviate, update PG status."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import boto3
from fastapi import FastAPI
from sqlalchemy import text

from shared.models.messages import SQS3Message
from shared.utils.dlq_monitor import monitor_loop

from .audit_writer import write_chunk_audit
from .config import settings
from .coordinator import maybe_complete_document, maybe_complete_indexing_job
from .db import SessionLocal
from .pg_updater import increment_chunks_indexed
from .weaviate_writer import WeaviateWriter

logger = logging.getLogger(__name__)

_writer = WeaviateWriter(weaviate_url=settings.weaviate_url)


async def _fetch_title(doc_id: str) -> str:
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT title FROM documents WHERE doc_id = :doc_id"),
            {"doc_id": doc_id},
        )
        row = result.fetchone()
        return row[0] if row else ""


async def _process_message(body: str) -> None:
    msg = SQS3Message.model_validate_json(body)
    logger.info("Indexing chunk_id=%s for doc_id=%s", msg.chunk_id, msg.doc_id)

    title = await _fetch_title(msg.doc_id)

    # Write to Weaviate (sync call wrapped in thread to avoid blocking event loop)
    await asyncio.to_thread(_writer.upsert, msg, title)

    # Update PostgreSQL and check for completion
    async with SessionLocal() as session:
        chunks_indexed, chunks_total = await increment_chunks_indexed(session, msg.doc_id)
        await write_chunk_audit(
            session,
            doc_id=msg.doc_id,
            chunk_id=msg.chunk_id,
            index_name=msg.target_index,
        )
        completed = await maybe_complete_document(session, msg.doc_id, chunks_indexed, chunks_total)
        if completed:
            await maybe_complete_indexing_job(session, msg.doc_id)
        await session.commit()


async def _consume_sqs_3() -> None:
    sqs = boto3.client(
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
    )
    logger.info("Indexing Service consumer started — polling SQS 3")

    while True:
        response = await asyncio.to_thread(
            sqs.receive_message,
            QueueUrl=settings.sqs_queue_3_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )
        messages = response.get("Messages", [])
        if not messages:
            continue

        for message in messages:
            receipt_handle = message["ReceiptHandle"]
            try:
                await _process_message(message["Body"])
                await asyncio.to_thread(
                    sqs.delete_message,
                    QueueUrl=settings.sqs_queue_3_url,
                    ReceiptHandle=receipt_handle,
                )
            except Exception as exc:
                logger.error(
                    "Failed to process SQS 3 message (will not delete → DLQ after retries): %s",
                    exc,
                    exc_info=True,
                )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    dlq_urls = [
        settings.sqs_dlq_1_url,
        settings.sqs_dlq_2_url,
        settings.sqs_dlq_3_url,
    ]
    consumer_task = asyncio.create_task(_consume_sqs_3())
    dlq_task = asyncio.create_task(
        monitor_loop(
            dlq_urls=dlq_urls,
            webhook_url=settings.dlq_alert_webhook_url,
            region=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url,
        )
    )
    try:
        yield
    finally:
        for task in (consumer_task, dlq_task):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await asyncio.to_thread(_writer.close)


app = FastAPI(title="Indexing Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, log_level="info")
