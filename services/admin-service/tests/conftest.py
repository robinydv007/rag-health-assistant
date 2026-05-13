import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

_svc = str(Path(__file__).parent.parent)
if _svc not in sys.path:
    sys.path.insert(0, _svc)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_sqs():
    client = MagicMock()
    client.get_queue_attributes.return_value = {
        "Attributes": {"ApproximateNumberOfMessages": "0"}
    }
    client.receive_message.return_value = {"Messages": []}
    client.send_message.return_value = {"MessageId": "test-msg-id"}
    client.delete_message.return_value = {}
    return client


@pytest.fixture
def mock_weaviate():
    client = MagicMock()
    client.schema.create_class.return_value = None
    client.schema.delete_class.return_value = None
    client.schema.get_class_shards.side_effect = Exception("not found")
    return client


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=httpx.AsyncClient)
