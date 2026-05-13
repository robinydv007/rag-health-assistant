"""Unit tests for OpenAIEmbeddingClient and HTTPEndpointClient."""

import json

import httpx
import pytest
import respx

from shared.clients.embedding_client import HTTPEndpointClient, OpenAIEmbeddingClient

_OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"
_FAKE_ENDPOINT_URL = "http://fake-gpu-server/embed"
_FAKE_KEY = "sk_test"
_TEXTS = ["aspirin reduces fever", "metformin controls blood sugar"]
_DIMS = 3072
_EP_DIMS = 768

# OpenAI response format: {"data": [{"index": N, "embedding": [...]}, ...]}
_OAI_RESPONSE = {
    "data": [
        {"index": i, "embedding": [float(i) / 100] * _DIMS}
        for i in range(len(_TEXTS))
    ]
}
_EP_VECTORS = [[float(i)] * _EP_DIMS for i in range(len(_TEXTS))]


@respx.mock
@pytest.mark.asyncio
async def test_openai_client_request_body_and_response():
    """OpenAIEmbeddingClient sends correct request body and returns N×3072 floats."""
    respx.post(_OPENAI_EMBED_URL).mock(return_value=httpx.Response(200, json=_OAI_RESPONSE))
    client = OpenAIEmbeddingClient(api_key=_FAKE_KEY, model="text-embedding-3-large")
    result = await client.embed(_TEXTS)

    assert len(result) == len(_TEXTS)
    assert all(len(v) == _DIMS for v in result)

    call = respx.calls[0]
    body = json.loads(call.request.content)
    assert body == {"model": "text-embedding-3-large", "input": _TEXTS}
    assert call.request.headers["authorization"] == f"Bearer {_FAKE_KEY}"


@respx.mock
@pytest.mark.asyncio
async def test_openai_client_preserves_order_when_response_shuffled():
    """OpenAIEmbeddingClient sorts data by index even if response is unordered."""
    shuffled = {
        "data": [
            {"index": 1, "embedding": [0.9] * _DIMS},
            {"index": 0, "embedding": [0.1] * _DIMS},
        ]
    }
    respx.post(_OPENAI_EMBED_URL).mock(return_value=httpx.Response(200, json=shuffled))
    client = OpenAIEmbeddingClient(api_key=_FAKE_KEY, model="text-embedding-3-large")
    result = await client.embed(_TEXTS)

    assert result[0][0] == pytest.approx(0.1)
    assert result[1][0] == pytest.approx(0.9)


@respx.mock
@pytest.mark.asyncio
async def test_http_endpoint_client_request_body():
    """HTTPEndpointClient sends correct request body and returns vectors."""
    respx.post(_FAKE_ENDPOINT_URL).mock(return_value=httpx.Response(200, json=_EP_VECTORS))
    client = HTTPEndpointClient(url=_FAKE_ENDPOINT_URL, api_key="secret")
    result = await client.embed(_TEXTS)

    assert len(result) == len(_TEXTS)

    call = respx.calls[0]
    body = json.loads(call.request.content)
    assert body == {"inputs": _TEXTS}
    assert call.request.headers["authorization"] == "Bearer secret"


@respx.mock
@pytest.mark.asyncio
async def test_http_endpoint_client_no_auth():
    """HTTPEndpointClient omits Authorization header when api_key is None."""
    respx.post(_FAKE_ENDPOINT_URL).mock(return_value=httpx.Response(200, json=_EP_VECTORS))
    client = HTTPEndpointClient(url=_FAKE_ENDPOINT_URL, api_key=None)
    await client.embed(_TEXTS)
    call = respx.calls[0]
    assert "authorization" not in call.request.headers
