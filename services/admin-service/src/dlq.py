"""Admin Service — DLQ inspection and message requeue."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def inspect_dlq(sqs_client, dlq_url: str, max_messages: int = 10) -> dict:
    """Peek at DLQ messages without consuming them (VisibilityTimeout=0)."""
    resp = await asyncio.to_thread(
        sqs_client.receive_message,
        QueueUrl=dlq_url,
        MaxNumberOfMessages=min(max_messages, 10),
        VisibilityTimeout=0,
        AttributeNames=["ApproximateReceiveCount"],
        MessageAttributeNames=["All"],
    )
    raw = resp.get("Messages", [])
    messages = [
        {
            "message_id": m["MessageId"],
            "receipt_handle": m["ReceiptHandle"],
            "body_preview": m["Body"][:200],
            "retries": int(m.get("Attributes", {}).get("ApproximateReceiveCount", 0)),
        }
        for m in raw
    ]

    # Get accurate depth via queue attributes
    attrs = await asyncio.to_thread(
        sqs_client.get_queue_attributes,
        QueueUrl=dlq_url,
        AttributeNames=["ApproximateNumberOfMessages"],
    )
    count = int(attrs["Attributes"]["ApproximateNumberOfMessages"])

    return {"count": count, "messages": messages}


async def requeue_messages(
    sqs_client,
    dlq_url: str,
    main_queue_url: str,
    message_ids: list[str],
) -> dict:
    """Move specific messages from DLQ back to the main queue."""
    # Receive all visible messages to find the ones with matching IDs
    resp = await asyncio.to_thread(
        sqs_client.receive_message,
        QueueUrl=dlq_url,
        MaxNumberOfMessages=10,
        VisibilityTimeout=30,
        AttributeNames=["All"],
    )
    available = {m["MessageId"]: m for m in resp.get("Messages", [])}

    requeued = 0
    failed = 0

    for mid in message_ids:
        msg = available.get(mid)
        if msg is None:
            logger.warning("Message %s not found in DLQ (may be invisible or gone)", mid)
            failed += 1
            continue
        try:
            await asyncio.to_thread(
                sqs_client.send_message,
                QueueUrl=main_queue_url,
                MessageBody=msg["Body"],
            )
            await asyncio.to_thread(
                sqs_client.delete_message,
                QueueUrl=dlq_url,
                ReceiptHandle=msg["ReceiptHandle"],
            )
            requeued += 1
        except Exception as exc:
            logger.error("Failed to requeue message %s: %s", mid, exc)
            failed += 1

    return {"requeued": requeued, "failed": failed}
