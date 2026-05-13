"""Unit tests for DLQ monitor — depth check, log warning, webhook POST."""

import pytest
import respx
import httpx
import logging
from unittest.mock import MagicMock

from shared.utils.dlq_monitor import check_dlq_depths, alert_if_needed

_Q1 = "http://fake:9324/000000000000/dlq-1"
_Q2 = "http://fake:9324/000000000000/dlq-2"
_WEBHOOK = "http://webhook-server/dlq-alert"


def _make_sqs(depths: dict[str, int]):
    """Return a mock boto3 SQS client with configured queue depths."""
    sqs = MagicMock()

    def fake_get_attrs(QueueUrl, AttributeNames):
        depth = depths.get(QueueUrl, 0)
        return {"Attributes": {"ApproximateNumberOfMessages": str(depth)}}

    sqs.get_queue_attributes.side_effect = fake_get_attrs
    return sqs


def test_check_dlq_depths_returns_correct_values():
    """check_dlq_depths returns the depth for each configured DLQ."""
    sqs = _make_sqs({_Q1: 3, _Q2: 0})
    result = check_dlq_depths(sqs, [_Q1, _Q2])
    assert result[_Q1] == 3
    assert result[_Q2] == 0


def test_check_dlq_depths_skips_empty_url():
    """check_dlq_depths skips empty-string queue URLs."""
    sqs = _make_sqs({})
    result = check_dlq_depths(sqs, ["", _Q1])
    assert "" not in result


@respx.mock
@pytest.mark.asyncio
async def test_alert_logs_warning_and_posts_webhook_on_depth_gt_0(caplog):
    """alert_if_needed logs WARNING and POSTs webhook when depth > 0."""
    respx.post(_WEBHOOK).mock(return_value=httpx.Response(200))

    with caplog.at_level(logging.WARNING, logger="shared.utils.dlq_monitor"):
        await alert_if_needed({_Q1: 2}, webhook_url=_WEBHOOK)

    assert any("DLQ alert" in r.message for r in caplog.records)
    assert len(respx.calls) == 1
    import json
    payload = json.loads(respx.calls[0].request.content)
    assert payload["queue"] == _Q1
    assert payload["depth"] == 2


@pytest.mark.asyncio
async def test_alert_no_action_when_depth_zero(caplog):
    """alert_if_needed produces no log or webhook when all queues are empty."""
    with caplog.at_level(logging.WARNING):
        await alert_if_needed({_Q1: 0, _Q2: 0}, webhook_url=_WEBHOOK)

    assert not any("DLQ" in r.message for r in caplog.records)
