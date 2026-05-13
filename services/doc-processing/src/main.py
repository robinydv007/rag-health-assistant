"""Doc Processing Service — SQS 1 consumer: download → scrub PII → parse → chunk → SQS 2."""

from __future__ import annotations

import asyncio
import logging

import boto3
from sqlalchemy import text

from shared.clients.s3_client import make_s3_client
from shared.config.settings import BaseServiceSettings
from shared.models.document import DocType
from shared.models.messages import SQS1Message, SQS2Chunk, SQS2Message

from .chunker import chunk_pages
from .db import SessionLocal
from .parsers import docx_parser, pdf_parser, txt_parser
from .scrubber import scrub

logger = logging.getLogger(__name__)

_settings = BaseServiceSettings()

_s3 = make_s3_client(
    bucket=_settings.s3_bucket,
    region=_settings.aws_region,
    endpoint_url=_settings.s3_endpoint_url,
    minio_user=_settings.minio_root_user if _settings.s3_endpoint_url else None,
    minio_password=_settings.minio_root_password if _settings.s3_endpoint_url else None,
)

_PARSERS = {
    "application/pdf": pdf_parser.parse,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": docx_parser.parse,
    "text/plain": txt_parser.parse,
}


async def _process_message(body: str) -> None:
    msg = SQS1Message.model_validate_json(body)
    logger.info("Processing doc_id=%s content_type=%s", msg.doc_id, msg.content_type)

    # Download from S3 / MinIO
    raw_bytes = await _s3.download(msg.s3_key)

    # PII scrub — apply to the raw text after parsing
    parser = _PARSERS.get(msg.content_type)
    if parser is None:
        raise ValueError(f"No parser for content_type={msg.content_type!r}")

    pages = parser(raw_bytes)
    scrubbed_pages = [(scrub(text), page_num) for text, page_num in pages]

    # Chunk
    chunks = chunk_pages(
        pages=scrubbed_pages,
        doc_id=msg.doc_id,
        doc_type=_content_type_to_doc_type(msg.content_type),
        target_index=msg.target_index,
    )

    # Publish to SQS 2
    sqs2_chunks = [
        SQS2Chunk(
            chunk_id=f"{msg.doc_id}_chunk_{c.metadata.chunk_idx:04d}",
            text=c.text,
            metadata=c.metadata,
        )
        for c in chunks
    ]
    sqs2_msg = SQS2Message(doc_id=msg.doc_id, chunks=sqs2_chunks)

    sqs = boto3.client(
        "sqs",
        region_name=_settings.aws_region,
        endpoint_url=_settings.aws_endpoint_url,
    )
    sqs.send_message(
        QueueUrl=_settings.sqs_queue_2_url,
        MessageBody=sqs2_msg.model_dump_json(),
    )

    # Update documents table
    async with SessionLocal() as session:
        await session.execute(
            text("""
                UPDATE documents
                SET status = 'processing', chunks_total = :chunks_total, updated_at = NOW()
                WHERE doc_id = :doc_id
            """),
            {"chunks_total": len(chunks), "doc_id": msg.doc_id},
        )
        await session.commit()

    logger.info(
        "doc_id=%s processed: %d chunks published to SQS 2", msg.doc_id, len(chunks)
    )


def _content_type_to_doc_type(content_type: str) -> DocType:
    mapping = {
        "application/pdf": DocType.other,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocType.other,
        "text/plain": DocType.other,
    }
    return mapping.get(content_type, DocType.other)


async def consume_sqs_1() -> None:
    """Main SQS 1 consumer loop — long-polls, processes, deletes on success."""
    logger.info("Doc Processing Service started — polling SQS 1")
    sqs = boto3.client(
        "sqs",
        region_name=_settings.aws_region,
        endpoint_url=_settings.aws_endpoint_url,
    )

    while True:
        response = await asyncio.to_thread(
            sqs.receive_message,
            QueueUrl=_settings.sqs_queue_1_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            AttributeNames=["ApproximateReceiveCount"],
        )
        messages = response.get("Messages", [])
        if not messages:
            continue

        for message in messages:
            receipt_handle = message["ReceiptHandle"]
            try:
                await _process_message(message["Body"])
                # Delete on success
                await asyncio.to_thread(
                    sqs.delete_message,
                    QueueUrl=_settings.sqs_queue_1_url,
                    ReceiptHandle=receipt_handle,
                )
            except Exception as exc:
                logger.error(
                    "Failed to process SQS 1 message (will not delete → DLQ after retries): %s",
                    exc,
                    exc_info=True,
                )
                # Do NOT delete — visibility timeout expires → SQS retries → DLQ


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(consume_sqs_1())
