# Phase 2 — Implementation Plan

```
Sequential:  Group 0 → (Groups 1 + 2 + 3 in parallel) → Group 4 → Group 5
```

---

## Group 0 — Contracts, Infrastructure & Shared Prerequisites

**Sequential.** Blocks all other groups.
**Dependencies**: Phase 1 complete (`shared/clients/`, docker-compose with MinIO + SQS 1/2, Alembic baseline)
**Commit**: `feat(infra): add SQS 3, embedding client abstraction, chunk_audit migration, Phase 2 deps`

### Tasks

1. Add SQS 3 + DLQ 3 to `docker-compose.yml` — same ElasticMQ/local SQS pattern as SQS 1 and 2; expose as `SQS_3_URL` and `DLQ_3_URL`
2. Add `embedding-service` and `indexing-service` to `docker-compose.yml` — build from their Dockerfiles; configure env vars; depends_on postgres, weaviate, SQS 3
3. Create `shared/clients/embedding_client.py`:
   - Abstract base: `EmbeddingClient.embed(texts: list[str]) -> list[list[float]]`
   - `HFInferenceClient`: `POST {HF_INFERENCE_URL}` with `{"inputs": [...]}` → `[[float, ...], ...]`; auth via `Authorization: Bearer {HF_API_KEY}`; handles 503 (model loading) with retry
   - `HTTPEndpointClient`: same request/response contract for self-hosted GPU (Triton, vLLM, custom FastAPI); auth via `Authorization: Bearer {EMBEDDING_API_KEY}` if set
   - Factory function `get_embedding_client()`: reads `EMBEDDING_PROVIDER` env var (`hf_inference` | `http_endpoint`); returns correct implementation
4. Add `chunk_audit` Alembic migration (`alembic/versions/`): create table matching data-model spec; add index on `doc_id`
5. Verify `indexing_jobs` Alembic migration exists — if missing, add it now (table is in data-model spec, needed by Phase 3 admin re-index)
6. Add Phase 2 deps to service `requirements.txt` files:
   - `services/embedding-service/requirements.txt`: `httpx`, `sqlalchemy[asyncio]`, `asyncpg`, `boto3`, `pydantic-settings`
   - `services/indexing-service/requirements.txt`: `httpx`, `weaviate-client`, `sqlalchemy[asyncio]`, `asyncpg`, `boto3`, `pydantic-settings`
   - `services/chat-service/requirements.txt`: add `httpx` if not present
7. Update `.env.example` with new vars:
   - `EMBEDDING_PROVIDER` (default: `hf_inference`)
   - `HF_INFERENCE_URL` (HF model endpoint URL)
   - `HF_API_KEY` (HF token)
   - `EMBEDDING_ENDPOINT_URL` (self-hosted GPU endpoint, used when `EMBEDDING_PROVIDER=http_endpoint`)
   - `EMBEDDING_API_KEY` (optional auth for self-hosted endpoint)
   - `SQS_3_URL`, `DLQ_3_URL`, `DLQ_ALERT_WEBHOOK_URL`
8. Write ADR 0003 amendment `specs/decisions/0003a-biomedbert-hf-inference-api.md`: documents the switch from self-hosted BioGPT/SciBERT on EC2 GPU to `BiomedNLP-BiomedBERT` via HF Serverless Inference API; records provider abstraction pattern and self-hosted switch path

---

## Group 1 — Embedding Service

**Parallel with Groups 2 and 3.**
**Dependencies**: Group 0 complete (embedding client, SQS 3 in compose, requirements)
**Commit**: `feat(embedding): SQS 2 consumer, BiomedBERT batching, SQS 3 publisher`

### Tasks

1. Implement SQS 2 consumer loop (`services/embedding-service/src/main.py`):
   - Long-poll SQS 2 (`WaitTimeSeconds=20`, `MaxNumberOfMessages=1`)
   - Parse `ChunkEmbeddingJob` from message body
   - Update `documents.status = embedding` in PostgreSQL
   - Dispatch to batch accumulator
   - On success: delete SQS 2 message
   - On failure: log error, do NOT delete — visibility timeout expires → DLQ 2 after 3 retries
2. Implement batch accumulator (`services/embedding-service/src/batcher.py`):
   - Accumulate chunks in-memory up to 64 items or 10 seconds (whichever comes first)
   - On flush: call `EmbeddingClient.embed(texts)` with the batch
   - Map returned vectors back to their source chunk IDs
3. Implement SQS 3 publisher (`services/embedding-service/src/publisher.py`):
   - For each `(chunk, vector)` pair, publish one `IndexingJob` message to SQS 3
   - Message schema matches `SQS 3 — Indexing Job` from `specs/architecture/api-reference.md`
4. Implement `GET /health` endpoint — returns HTTP 200 + `{"status": "ok"}`
5. Unit test — `HFInferenceClient` with mocked `httpx`: assert request body is `{"inputs": [text, ...]}`, assert returned list has correct shape (N texts × 768 floats)
6. Unit test — `HTTPEndpointClient` with mocked `httpx`: same interface contract
7. Unit test — batch accumulator: flushes exactly at 64 chunks; flushes on 10s timeout without waiting for full batch
8. Unit test — SQS 3 publisher: output message matches `IndexingJob` schema; `chunk_id`, `embedding`, `metadata`, `target_index` all present
9. Integration test (`services/embedding-service/tests/test_embedding_integration.py`): place a `ChunkEmbeddingJob` message on SQS 2 → assert SQS 3 contains messages where `embedding` is a list of 768 floats; assert `documents.status = embedding` in PostgreSQL

---

## Group 2 — Indexing Service

**Parallel with Groups 1 and 3.**
**Dependencies**: Group 0 complete (chunk_audit migration, SQS 3, weaviate-client dep)
**Commit**: `feat(indexing): SQS 3 consumer, Weaviate writer, coordinator, DLQ monitor`

### Tasks

1. Implement SQS 3 consumer loop (`services/indexing-service/src/main.py`):
   - Long-poll SQS 3 (`WaitTimeSeconds=20`, `MaxNumberOfMessages=1`)
   - Parse `IndexingJob` from message body
   - Dispatch to Weaviate writer
   - On success: delete SQS 3 message
   - On failure: log error, do NOT delete — DLQ 3 after 3 retries
2. Implement Weaviate writer (`services/indexing-service/src/weaviate_writer.py`):
   - Upsert `KnowledgeChunk` object to Weaviate using `with_id(chunk_id)` to allow idempotent retries
   - Set all properties from `IndexingJob` metadata: `docId`, `chunkId`, `chunkIdx`, `text`, `docType`, `title`, `pageNum`, `version`, `embeddedModel`, `indexedAt`
   - Pass vector via `with_vector(embedding)` — Weaviate `vectorizer: none`
   - Write to index specified by `target_index` field (`live` or `shadow`)
3. Implement PostgreSQL updater (`services/indexing-service/src/pg_updater.py`):
   - `increment_chunks_indexed(doc_id)`: `UPDATE documents SET chunks_indexed = chunks_indexed + 1 WHERE doc_id = $1`
   - Returns updated `(chunks_indexed, chunks_total)` tuple for coordinator
4. Implement `chunk_audit` writer (`services/indexing-service/src/audit_writer.py`):
   - Insert one row per chunk: `doc_id`, `chunk_id`, `index_name`, `embedded_model = "BiomedBERT"`, `written_at = NOW()`
5. Implement Indexing Coordinator (`services/indexing-service/src/coordinator.py`):
   - Called after each successful PG increment
   - If `chunks_indexed == chunks_total`: `UPDATE documents SET status = 'indexed' WHERE doc_id = $1`
   - Log `"Document {doc_id} fully indexed — {chunks_total} chunks"` at INFO level
6. Implement DLQ monitor (`shared/utils/dlq_monitor.py`):
   - `check_dlq_depths(sqs_client, dlq_urls: list[str]) -> dict[str, int]`: returns depth per DLQ URL
   - `alert_if_needed(depths: dict[str, int], webhook_url: str | None)`: logs WARNING for any depth > 0; if `webhook_url` is set, POSTs `{"queue": url, "depth": N}` via `httpx`
   - Called on a background loop in the Indexing Service every 60 seconds
7. Implement `GET /health` endpoint — returns HTTP 200 + `{"status": "ok"}`
8. Unit test — Weaviate writer: mock Weaviate client; assert object properties match message fields; assert `with_vector` called with correct-length list
9. Unit test — PG completion tracking: `chunks_indexed == chunks_total` → coordinator sets `status = indexed`; `chunks_indexed < chunks_total` → no status change
10. Unit test — `chunk_audit` writer: assert row inserted with `embedded_model = "BiomedBERT"` and correct `doc_id`
11. Unit test — DLQ monitor: depth > 0 → WARNING logged + `httpx.post` called with queue name; depth = 0 → no alert
12. Integration test (`services/indexing-service/tests/test_indexing_integration.py`): place an `IndexingJob` on SQS 3 → assert Weaviate contains `KnowledgeChunk` with matching `chunkId` + `documents.chunks_indexed` incremented + `chunk_audit` row present in PostgreSQL

---

## Group 3 — Chat Service Update

**Parallel with Groups 1 and 2.**
**Dependencies**: Group 0 complete (embedding client, chat-service httpx dep)
**Commit**: `feat(chat): replace zero-vectors with BiomedBERT query embedding`

### Tasks

1. Update `services/chat-service/src/searcher.py`:
   - Import `get_embedding_client` from `shared/clients/embedding_client.py`
   - Replace `[0.0] * 768` zero-vector with `await embedding_client.embed([query])` call
   - Cache the client instance at module level (initialised once at startup)
2. Add embedding env vars to `services/chat-service/src/config.py`: `EMBEDDING_PROVIDER`, `HF_INFERENCE_URL`, `HF_API_KEY`
3. Update `services/chat-service/tests/test_searcher.py`:
   - Mock `EmbeddingClient.embed()` to return a deterministic non-zero vector
   - Assert the mocked vector is passed to Weaviate `nearVector` — not a zero-vector
4. Integration test update (`services/chat-service/tests/test_integration.py`):
   - Seed Weaviate fixture chunks with real BiomedBERT vectors (pre-computed from the HF API, stored as fixture JSON)
   - Call `/ask` with a related question
   - Assert `body["sources"][0]["title"]` matches the seeded fixture doc — verifying semantic search is working
   - Note: `/ask` returns full JSON (`{"answer": ..., "sources": [...]}`); no SSE assertions needed

---

## Group 4 — Wiring & Integration

**Sequential.** Runs after Groups 1, 2, and 3 are complete.
**Dependencies**: All three service implementations done
**Commit**: `test(integration): Phase 2 end-to-end embedding and indexing pipeline`

### Tasks

1. `docker-compose up --build` → all 8 services (6 original + embedding-service + indexing-service) and infrastructure (MinIO, SQS 1/2/3 + DLQs, Weaviate, PostgreSQL) healthy
2. End-to-end upload test: POST PDF → MinIO object + `documents.status = pending` + SQS 1 message
3. End-to-end doc processing test: SQS 1 → SQS 2 chunks + `documents.status = processing`
4. End-to-end embedding test: SQS 2 → Embedding Service polls → SQS 3 messages appear; each message has `embedding` as a list of 768 floats; `documents.status = embedding` in PostgreSQL
5. End-to-end indexing test: SQS 3 → Indexing Service polls → Weaviate `KnowledgeChunk` object exists with correct `chunkId`; `documents.status = indexed`; `chunk_audit` row present
6. End-to-end ask test: call `/ask` with a question semantically related to the indexed doc → SSE stream returns relevant chunk in sources (not a random chunk)
7. Smoke test all 8 `/health` endpoints → HTTP 200

---

## Group 5 — Verification

**Sequential.** Runs after Group 4.
**Dependencies**: All integration tests passing
**Commit**: `chore: Phase 2 verification — all tests pass`

### Tasks

1. Run full test suite per-service: `pytest services/ shared/ -v --tb=short` → exit 0 (add `embedding-service` and `indexing-service` to CI matrix using same `PYTHONPATH=services/<svc>` pattern from Phase 1)
2. Run linter: `ruff check services/ shared/` → exit 0
3. Run type checker: `mypy shared/ --ignore-missing-imports` → exit 0
4. Confirm CI passes on clean push to `phase-2-embedding-indexing` branch
5. Update `specs/status.md` — mark Phase 2 complete, update progress
