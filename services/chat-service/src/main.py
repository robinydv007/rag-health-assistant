"""Chat Service — handles user queries, hybrid search, and LLM streaming responses."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Chat Service", version="0.1.0")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "chat-service"})


# TODO Phase 1: POST /api/v1/knowledge/ask — query expand → hybrid search → rerank → LLM → SSE stream
# TODO Phase 1: GET /api/v1/knowledge/history — paginated query history
