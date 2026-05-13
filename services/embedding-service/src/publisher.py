"""SQS 3 publisher — one IndexingJob message per embedded chunk."""

from __future__ import annotations

import asyncio
import logging

import boto3

from shared.models.chunk import ChunkMetadata
from shared.models.messages import SQS3Message

logger = logging.getLogger(__name__)


class SQS3Publisher:
    def __init__(self, queue_url: str, region: str, endpoint_url: str | None = None) -> None:
        self._queue_url = queue_url
        self._sqs = boto3.client(
            "sqs",
            region_name=region,
            endpoint_url=endpoint_url,
        )

    async def publish(
        self,
        doc_id: str,
        chunk_id: str,
        text: str,
        embedding: list[float],
        metadata: ChunkMetadata,
    ) -> None:
        msg = SQS3Message(
            doc_id=doc_id,
            chunk_id=chunk_id,
            text=text,
            embedding=embedding,
            metadata=metadata,
            target_index=metadata.target_index,
        )
        await asyncio.to_thread(
            self._sqs.send_message,
            QueueUrl=self._queue_url,
            MessageBody=msg.model_dump_json(),
        )
        logger.debug("Published IndexingJob chunk_id=%s to SQS 3", chunk_id)
