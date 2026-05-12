"""Admin Service — internal ops: re-index, alias swap, DLQ management, health check."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Admin Service", version="0.1.0")


@app.get("/api/v1/health")
async def health() -> JSONResponse:
    # TODO Phase 3: aggregate health from all services, queues, and databases
    return JSONResponse({
        "status": "healthy",
        "service": "admin-service",
        "note": "Aggregate health check not yet implemented — Phase 3"
    })


# TODO Phase 3: POST /admin/reindex — trigger zero-downtime full re-index
# TODO Phase 3: POST /admin/swap-index — swap alias after re-index completes
# TODO Phase 3: GET /admin/dlq — inspect all DLQs
# TODO Phase 3: POST /admin/dlq/requeue — requeue messages from DLQ
