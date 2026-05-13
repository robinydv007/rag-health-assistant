"""Embedding Service — SQS 2 consumer: BiomedBERT vectorization → SQS 3."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import boto3
from fastapi import FastAPI
from sqlalchemy import text

from shared.clients.embedding_client import get_embedding_client
from shared.models.messages import SQS2Message

from .batcher import Batcher
from .config import settings
from .db import SessionLocal
from .publisher import SQS3Publisher

logger = logging.getLogger(__name__)

_embedding_client = get_embedding_client()
_publisher = SQS3Publisher(
    queue_url=settings.sqs_queue_3_url,
    region=settings.aws_region,
    endpoint_url=settings.aws_endpoint_url,
)


async def _process_message(body: str) -> None:
    msg = SQS2Message.model_validate_json(body)
    logger.info("Embedding doc_id=%s with %d chunks", msg.doc_id, len(msg.chunks))

    # Mark document as embedding
    async with SessionLocal() as session:
        await session.execute(
            text(
                "UPDATE documents SET status = 'embedding', updated_at = NOW()"
                " WHERE doc_id = :doc_id"
            ),
            {"doc_id": msg.doc_id},
        )
        await session.commit()

    # Embed in batches of up to 64 via the batcher
    batcher = Batcher(embed_fn=_embedding_client.embed)
    all_results: list[tuple[str, list[float]]] = []

    for chunk in msg.chunks:
        results = await batcher.add(chunk.chunk_id, chunk.text)
        all_results.extend(results)

    # Drain any remaining chunks below the flush threshold
    all_results.extend(await batcher.drain())

    # Map chunk_id → (text, metadata) for publishing
    chunk_info = {c.chunk_id: (c.text, c.metadata) for c in msg.chunks}

    # Publish one SQS 3 message per chunk
    for chunk_id, embedding in all_results:
        chunk_text, meta = chunk_info[chunk_id]
        await _publisher.publish(
            doc_id=msg.doc_id,
            chunk_id=chunk_id,
            text=chunk_text,
            embedding=embedding,
            metadata=meta,
        )

    logger.info(
        "doc_id=%s embedded and published %d IndexingJob messages to SQS 3",
        msg.doc_id,
        len(all_results),
    )


async def _consume_sqs_2() -> None:
    sqs = boto3.client(
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
    )
    logger.info("Embedding Service consumer started — polling SQS 2")

    while True:
        response = await asyncio.to_thread(
            sqs.receive_message,
            QueueUrl=settings.sqs_queue_2_url,
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
                    QueueUrl=settings.sqs_queue_2_url,
                    ReceiptHandle=receipt_handle,
                )
            except Exception as exc:
                logger.error(
                    "Failed to process SQS 2 message (will not delete → DLQ after retries): %s",
                    exc,
                    exc_info=True,
                )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    task = asyncio.create_task(_consume_sqs_2())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Embedding Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, log_level="info")
