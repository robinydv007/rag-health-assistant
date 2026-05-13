"""DLQ depth monitor with log alerting and optional webhook notification."""

from __future__ import annotations

import asyncio
import logging

import boto3
import httpx

logger = logging.getLogger(__name__)


def check_dlq_depths(
    sqs_client,
    dlq_urls: list[str],
) -> dict[str, int]:
    """Return the approximate message count for each DLQ URL.

    Args:
        sqs_client: boto3 SQS client (synchronous).
        dlq_urls: List of DLQ queue URLs to check.

    Returns:
        Mapping of queue_url → approximate message depth.
    """
    depths: dict[str, int] = {}
    for url in dlq_urls:
        if not url:
            continue
        try:
            attrs = sqs_client.get_queue_attributes(
                QueueUrl=url,
                AttributeNames=["ApproximateNumberOfMessages"],
            )
            depths[url] = int(
                attrs["Attributes"].get("ApproximateNumberOfMessages", "0")
            )
        except Exception as exc:
            logger.warning("Could not check DLQ %s: %s", url, exc)
            depths[url] = -1
    return depths


async def alert_if_needed(
    depths: dict[str, int],
    webhook_url: str | None = None,
) -> None:
    """Log WARNING for any DLQ with depth > 0; POST to webhook if configured.

    Args:
        depths: Mapping of queue_url → depth, as returned by check_dlq_depths.
        webhook_url: Optional URL to POST an alert payload to.
    """
    for queue_url, depth in depths.items():
        if depth <= 0:
            continue
        logger.warning("DLQ alert: %s has %d message(s)", queue_url, depth)
        if webhook_url:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        webhook_url,
                        json={"queue": queue_url, "depth": depth},
                    )
            except Exception as exc:
                logger.warning("Failed to POST DLQ alert to webhook: %s", exc)


async def monitor_loop(
    dlq_urls: list[str],
    webhook_url: str | None,
    region: str,
    endpoint_url: str | None,
    poll_interval: float = 60.0,
) -> None:
    """Background task: check DLQ depths every poll_interval seconds."""
    sqs = boto3.client(
        "sqs",
        region_name=region,
        endpoint_url=endpoint_url,
    )
    while True:
        depths = await asyncio.to_thread(check_dlq_depths, sqs, dlq_urls)
        await alert_if_needed(depths, webhook_url)
        await asyncio.sleep(poll_interval)
