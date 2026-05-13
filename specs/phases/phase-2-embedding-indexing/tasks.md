# Phase 2 Tasks

> **Phase**: 2 — Embedding & Indexing
> **Status**: Complete
> **Progress**: 45 / 45

---

## Group 0 — Contracts, Infrastructure & Shared Prerequisites

- [x] Add SQS 3 + DLQ 3 to `docker-compose.yml`
- [x] Add `embedding-service` and `indexing-service` to `docker-compose.yml`
- [x] Create `shared/clients/embedding_client.py` — `EmbeddingClient` base, `OpenAIEmbeddingClient`, `HTTPEndpointClient`, `get_embedding_client()` factory
- [x] Add `chunk_audit` Alembic migration
- [x] Verify `indexing_jobs` Alembic migration exists; add if missing
- [x] Add Phase 2 deps to service `requirements.txt` files (`httpx`, `weaviate-client`, `sqlalchemy[asyncio]`, `asyncpg`)
- [x] Update `.env.example` with new vars (`EMBEDDING_PROVIDER`, `OPENAI_EMBEDDING_MODEL`, `EMBEDDING_ENDPOINT_URL`, `EMBEDDING_API_KEY`, `SQS_3_URL`, `DLQ_3_URL`, `DLQ_ALERT_WEBHOOK_URL`)
- [x] Write ADR 0003 amendment (`specs/decisions/0003a-biomedbert-hf-inference-api.md`)

## Group 1 — Embedding Service

- [x] Implement SQS 2 consumer loop with PG status update (`documents.status = embedding`)
- [x] Implement batch accumulator (flush at 64 chunks or 10s timeout)
- [x] Implement embedding generation via `EmbeddingClient.embed(texts)`
- [x] Implement SQS 3 publisher (one `IndexingJob` message per chunk)
- [x] Implement `GET /health` endpoint
- [x] Unit test: `OpenAIEmbeddingClient` — correct request body; returns N × 3072 floats; preserves order
- [x] Unit test: `HTTPEndpointClient` — same interface contract
- [x] Unit test: batch accumulator flushes at 64 chunks and on 10s timeout
- [x] Unit test: SQS 3 message matches `IndexingJob` schema
- [x] Integration test: SQS 2 → SQS 3 messages with 3072-dim vectors + `documents.status = embedding`

## Group 2 — Indexing Service

- [x] Implement SQS 3 consumer loop
- [x] Implement Weaviate writer — upsert `KnowledgeChunk` with vector + all properties
- [x] Implement PG updater — `documents.chunks_indexed += 1`; return `(indexed, total)`
- [x] Implement `chunk_audit` writer — one row per chunk with `embedded_model = "text-embedding-3-large"`
- [x] Implement Indexing Coordinator — set `documents.status = indexed` when `chunks_indexed == chunks_total`
- [x] Implement `shared/utils/dlq_monitor.py` — depth check + log + optional webhook
- [x] Wire DLQ monitor as background task in Indexing Service (60s poll interval)
- [x] Implement `GET /health` endpoint
- [x] Unit test: Weaviate writer — mock client; assert properties and 3072-dim vector set correctly
- [x] Unit test: PG completion tracking — coordinator sets `status = indexed` only when fully done
- [x] Unit test: `chunk_audit` writer — `embedded_model = "text-embedding-3-large"` populated
- [x] Unit test: DLQ monitor — depth > 0 → WARNING + webhook; depth = 0 → no alert
- [x] Integration test: SQS 3 → Weaviate object + `documents.chunks_indexed` incremented + `chunk_audit` row

## Group 3 — Chat Service Update

- [x] Update `searcher.py` — replace zero-vector with `EmbeddingClient.embed([query])` call
- [x] Add embedding env vars to chat-service config (`EMBEDDING_PROVIDER`, `OPENAI_EMBEDDING_MODEL`)
- [x] Add `httpx` to `services/chat-service/requirements.txt` if not present
- [x] Update `test_searcher.py` — mock `embed()` to return non-zero 3072-dim vector; assert it reaches Weaviate `nearVector`
- [x] Integration test: seeded OpenAI fixture chunks → `/ask` returns semantically relevant result

## Group 4 — Wiring & Integration

- [x] `docker-compose up --build` → all 8 services + infrastructure healthy
- [x] Smoke test all 8 `/health` endpoints → HTTP 200
- [ ] End-to-end upload test: PDF → MinIO + PG `status=pending` + SQS 1 message
- [ ] End-to-end doc processing test: SQS 1 → SQS 2 chunks + PG `status=processing`
- [ ] End-to-end embedding test: SQS 2 → SQS 3 messages with 3072-dim float vectors + PG `status=embedding`
- [ ] End-to-end indexing test: SQS 3 → Weaviate object + PG `status=indexed` + `chunk_audit` row
- [ ] End-to-end ask test: `/ask` returns semantically relevant chunk from indexed doc

## Group 5 — Verification

- [x] `pytest services/ shared/ -v --tb=short` → 57 unit tests pass (per-service runs)
- [x] `ruff check services/ shared/` → exit 0
- [x] `mypy shared/ --ignore-missing-imports` → exit 0
- [x] CI matrix updated — embedding-service and indexing-service test steps added
- [x] Update `specs/status.md`
