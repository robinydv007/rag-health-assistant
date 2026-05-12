"""Chat Service — handles user queries, hybrid search, and LLM streaming responses."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from shared.models.query import AskRequest

app = FastAPI(title="Chat Service", version="0.1.0")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "chat-service"})


@app.post("/api/v1/knowledge/ask")
async def ask(request: AskRequest) -> JSONResponse:
    # Phase 0 stub — accepts correct request shape, returns mock
    # Phase 1: query expand → hybrid search → rerank → LLM → SSE stream
    return JSONResponse({
        "stub": True,
        "question": request.question,
        "answer": "Phase 0 stub — real response in Phase 1",
        "sources": [],
    })


@app.get("/api/v1/knowledge/history")
async def history(user_id: str, limit: int = 20, offset: int = 0) -> JSONResponse:
    # Phase 1: query PostgreSQL query_history for user
    return JSONResponse({"stub": True, "queries": [], "total": 0})
