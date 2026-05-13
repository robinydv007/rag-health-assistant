"""Unit tests for Admin Service health aggregation."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.health import aggregate_health, check_postgres, check_service, check_weaviate


@pytest.mark.asyncio
async def test_check_service_healthy():
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.return_value = MagicMock(status_code=200)
    result = await check_service(client, "http://some-service:8000")
    assert result == "healthy"


@pytest.mark.asyncio
async def test_check_service_unhealthy_non_200():
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.return_value = MagicMock(status_code=503)
    result = await check_service(client, "http://some-service:8000")
    assert result == "unhealthy"


@pytest.mark.asyncio
async def test_check_service_unhealthy_on_exception():
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.side_effect = httpx.ConnectError("refused")
    result = await check_service(client, "http://some-service:8000")
    assert result == "unhealthy"


@pytest.mark.asyncio
async def test_check_postgres_healthy(mock_session):
    result = await check_postgres(mock_session)
    assert result == "healthy"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_postgres_unhealthy_on_exception(mock_session):
    mock_session.execute.side_effect = Exception("db down")
    result = await check_postgres(mock_session)
    assert result == "unhealthy"


@pytest.mark.asyncio
async def test_check_weaviate_healthy():
    with patch("src.health.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = MagicMock(status_code=200)
        result = await check_weaviate("http://weaviate:8080")
    assert result == "healthy"


@pytest.mark.asyncio
async def test_aggregate_health_all_healthy(mock_session, mock_sqs, mock_http_client):
    mock_http_client.get.return_value = MagicMock(status_code=200)

    with patch("src.health.httpx.AsyncClient") as mock_cls:
        mock_weaviate_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_weaviate_client
        mock_weaviate_client.get.return_value = MagicMock(status_code=200)

        result = await aggregate_health(mock_session, mock_sqs, mock_http_client)

    assert result["status"] == "healthy"
    assert result["postgres"] == "healthy"
    assert "services" in result
    assert "queues" in result


@pytest.mark.asyncio
async def test_aggregate_health_degraded_when_service_down(
    mock_session, mock_sqs, mock_http_client
):
    mock_http_client.get.side_effect = httpx.ConnectError("refused")

    with patch("src.health.httpx.AsyncClient") as mock_cls:
        mock_weaviate_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_weaviate_client
        mock_weaviate_client.get.return_value = MagicMock(status_code=200)

        result = await aggregate_health(mock_session, mock_sqs, mock_http_client)

    assert result["status"] == "degraded"
    assert all(v == "unhealthy" for v in result["services"].values())


@pytest.mark.asyncio
async def test_aggregate_health_degraded_when_weaviate_down(
    mock_session, mock_sqs, mock_http_client
):
    mock_http_client.get.return_value = MagicMock(status_code=200)

    with patch("src.health.httpx.AsyncClient") as mock_cls:
        mock_weaviate_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_weaviate_client
        mock_weaviate_client.get.side_effect = Exception("weaviate down")

        result = await aggregate_health(mock_session, mock_sqs, mock_http_client)

    assert result["status"] == "degraded"
    assert result["weaviate"] == "unhealthy"
