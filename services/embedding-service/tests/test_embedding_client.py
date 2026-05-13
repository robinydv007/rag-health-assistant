"""Unit tests for HFInferenceClient and HTTPEndpointClient."""

import json
import pytest
import httpx
import respx

from shared.clients.embedding_client import (
    HFInferenceClient,
    HTTPEndpointClient,
)

_FAKE_URL = "http://fake-hf-api/embed"
_FAKE_KEY = "hf_test"
_TEXTS = ["aspirin reduces fever", "metformin controls blood sugar"]
_VECTORS = [[float(i)] * 768 for i in range(len(_TEXTS))]


@respx.mock
@pytest.mark.asyncio
async def test_hf_inference_client_request_body():
    """HFInferenceClient sends correct request body and returns N×768 floats."""
    respx.post(_FAKE_URL).mock(
        return_value=httpx.Response(200, json=_VECTORS)
    )
    client = HFInferenceClient(url=_FAKE_URL, api_key=_FAKE_KEY)
    result = await client.embed(_TEXTS)

    assert len(result) == len(_TEXTS)
    assert all(len(v) == 768 for v in result)

    call = respx.calls[0]
    body = json.loads(call.request.content)
    assert body == {"inputs": _TEXTS}
    assert call.request.headers["authorization"] == f"Bearer {_FAKE_KEY}"


@respx.mock
@pytest.mark.asyncio
async def test_hf_inference_client_retries_on_503():
    """HFInferenceClient retries when model is loading (503 response)."""
    respx.post(_FAKE_URL).mock(
        side_effect=[
            httpx.Response(503, json={"estimated_time": 0.01}),
            httpx.Response(200, json=_VECTORS),
        ]
    )
    client = HFInferenceClient(url=_FAKE_URL, api_key=_FAKE_KEY)
    result = await client.embed(_TEXTS)
    assert len(result) == len(_TEXTS)
    assert len(respx.calls) == 2


@respx.mock
@pytest.mark.asyncio
async def test_http_endpoint_client_request_body():
    """HTTPEndpointClient sends correct request body and returns N×768 floats."""
    respx.post(_FAKE_URL).mock(
        return_value=httpx.Response(200, json=_VECTORS)
    )
    client = HTTPEndpointClient(url=_FAKE_URL, api_key="secret")
    result = await client.embed(_TEXTS)

    assert len(result) == len(_TEXTS)
    assert all(len(v) == 768 for v in result)

    call = respx.calls[0]
    body = json.loads(call.request.content)
    assert body == {"inputs": _TEXTS}
    assert call.request.headers["authorization"] == "Bearer secret"


@respx.mock
@pytest.mark.asyncio
async def test_http_endpoint_client_no_auth():
    """HTTPEndpointClient omits Authorization header when api_key is None."""
    respx.post(_FAKE_URL).mock(return_value=httpx.Response(200, json=_VECTORS))
    client = HTTPEndpointClient(url=_FAKE_URL, api_key=None)
    await client.embed(_TEXTS)
    call = respx.calls[0]
    assert "authorization" not in call.request.headers
