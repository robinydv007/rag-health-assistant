"""Unit tests for Admin Service DLQ inspection and requeue."""

from unittest.mock import patch

import pytest
from src.dlq import inspect_dlq, requeue_messages


@pytest.mark.asyncio
async def test_inspect_dlq_returns_count_and_messages(mock_sqs):
    mock_sqs.get_queue_attributes.return_value = {
        "Attributes": {"ApproximateNumberOfMessages": "3"}
    }
    mock_sqs.receive_message.return_value = {
        "Messages": [
            {
                "MessageId": "msg-1",
                "ReceiptHandle": "rh-1",
                "Body": '{"doc_id": "doc-1"}',
                "Attributes": {"ApproximateReceiveCount": "2"},
            }
        ]
    }

    with patch("src.dlq.asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        result = await inspect_dlq(mock_sqs, "http://sqs/dlq-1")

    assert result["count"] == 3
    assert len(result["messages"]) == 1
    assert result["messages"][0]["retries"] == 2
    assert result["messages"][0]["message_id"] == "msg-1"


@pytest.mark.asyncio
async def test_inspect_dlq_empty(mock_sqs):
    mock_sqs.get_queue_attributes.return_value = {
        "Attributes": {"ApproximateNumberOfMessages": "0"}
    }
    mock_sqs.receive_message.return_value = {"Messages": []}

    with patch("src.dlq.asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        result = await inspect_dlq(mock_sqs, "http://sqs/dlq-1")

    assert result["count"] == 0
    assert result["messages"] == []


@pytest.mark.asyncio
async def test_requeue_messages_success(mock_sqs):
    mock_sqs.receive_message.return_value = {
        "Messages": [
            {"MessageId": "msg-1", "ReceiptHandle": "rh-1", "Body": '{"doc_id": "doc-1"}'},
            {"MessageId": "msg-2", "ReceiptHandle": "rh-2", "Body": '{"doc_id": "doc-2"}'},
        ]
    }

    with patch("src.dlq.asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        result = await requeue_messages(
            mock_sqs,
            dlq_url="http://sqs/dlq-1",
            main_queue_url="http://sqs/queue-1",
            message_ids=["msg-1", "msg-2"],
        )

    assert result["requeued"] == 2
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_requeue_messages_partial_failure(mock_sqs):
    mock_sqs.receive_message.return_value = {
        "Messages": [
            {"MessageId": "msg-1", "ReceiptHandle": "rh-1", "Body": "{}"},
        ]
    }
    def send_fail(*args, **kwargs):
        raise Exception("sqs send failed")

    mock_sqs.send_message.side_effect = send_fail

    with patch("src.dlq.asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)):
        result = await requeue_messages(
            mock_sqs,
            dlq_url="http://sqs/dlq-1",
            main_queue_url="http://sqs/queue-1",
            message_ids=["msg-1", "msg-missing"],
        )

    assert result["failed"] == 2
    assert result["requeued"] == 0
