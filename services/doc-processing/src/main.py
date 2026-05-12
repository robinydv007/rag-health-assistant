"""Doc Processing Service — SQS 1 consumer: PII scrub → parse → chunk → SQS 2."""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def consume_sqs_1() -> None:
    """Main SQS 1 consumer loop. Phase 1 implementation pending."""
    logger.info("Doc Processing Service started. Awaiting SQS 1 messages.")
    # TODO Phase 1:
    # 1. Poll SQS 1 for messages
    # 2. Download file from S3
    # 3. Scrub PII/PHI (AWS Comprehend Medical / Presidio)
    # 4. Parse file format (PDF, DOCX, TXT, HL7)
    # 5. Chunk text (512 tokens, 50-token overlap)
    # 6. Tag metadata (doc_id, chunk_idx, version, target_index)
    # 7. Publish chunk batches to SQS 2
    # 8. Update PostgreSQL documents.status = 'embedding'
    while True:
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(consume_sqs_1())
