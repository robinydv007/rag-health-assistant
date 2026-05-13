# Phase 3 — Implementation Plan

```
Sequential:  Group 0 → (Groups 1 + 2 in parallel) → Group 3 → Group 4
```

## Reference Specs

| Spec | Relevance |
|------|-----------|
| `specs/architecture/services.md` | Admin Service endpoint contracts, LLM Router circuit breaker logic |
| `specs/architecture/api-reference.md` | Admin endpoint schemas, SQS 1 message schema |
| `specs/architecture/data-model.md` | `indexing_jobs` table, `documents` table |

---

## Group 0 — Circuit Breaker Types + Admin Service Deps

**Sequential.** Blocks all other groups.
**Dependencies**: Phase 2 complete (`shared/clients/llm_client.py` with registered providers)
**Commit**: `feat(llm-router): circuit breaker types and admin service deps`

### Tasks

1. Create `shared/llm_router/__init__.py` (empty — makes the package importable)
2. Create `shared/llm_router/circuit_breaker.py`:
   - `CircuitState` enum: `CLOSED`, `OPEN`, `HALF_OPEN`
   - `CircuitBreaker` class with `failure_threshold=3`, `timeout_threshold=5.0`, `reset_timeout=60.0`
   - `is_available() -> bool`: if OPEN → check `time.monotonic() - last_failure_time > reset_timeout`; transition to HALF_OPEN and return True if elapsed; else return False; CLOSED/HALF_OPEN → True
   - `record_success()`: reset `failure_count = 0`, set state = CLOSED
   - `record_failure()`: increment `failure_count`, set `last_failure_time = time.monotonic()`; if `failure_count >= failure_threshold` → state = OPEN
   - Module-level singleton: `_llm_circuit_breaker = CircuitBreaker()` (per-process in-memory state)
3. Add `httpx` and `weaviate-client` to `services/admin-service/requirements.txt` if not present
4. Create `services/admin-service/src/deps.py`:
   - `get_db()` — async SQLAlchemy session (same pattern as other services)
   - `get_sqs_client()` — boto3 SQS client from env vars (`AWS_REGION`, `AWS_ENDPOINT_URL`)
   - `get_weaviate_client()` — `weaviate.Client(url=settings.weaviate_url)`
   - `get_http_client()` — `httpx.AsyncClient()` for pinging service health endpoints
5. Create `services/admin-service/src/settings.py`:
   - Extend `BaseServiceSettings` with admin-specific env vars: service URLs for health check pings (`CHAT_SERVICE_URL`, `UPLOADER_SERVICE_URL`, etc.)

---

## Group 1 — Admin Service Endpoints

**Parallel with Group 2.**
**Dependencies**: Group 0 complete
**Commit**: `feat(admin): implement health, reindex, alias-swap, DLQ endpoints`

### Tasks

1. Create `services/admin-service/src/health.py`:
   - `async check_service(client: httpx.AsyncClient, url: str) -> str` — GET `{url}/api/v1/health`; return `"healthy"` or `"unhealthy"` on any error
   - `async check_postgres(session: AsyncSession) -> str` — execute `SELECT 1`; return `"healthy"` or `"unhealthy"`
   - `async check_weaviate(weaviate_url: str) -> str` — GET `{weaviate_url}/v1/health`
   - `async get_sqs_depth(sqs_client, queue_url: str) -> int` — `get_queue_attributes(AttributeNames=["ApproximateNumberOfMessages"])`
   - `async aggregate_health(...)` — assemble full response matching `GET /health` schema in `specs/architecture/api-reference.md`

2. Create `services/admin-service/src/reindex.py`:
   - `async trigger_reindex(reason: str, session, sqs_client, weaviate_client, settings) -> dict`:
     - Shadow index name: `f"KnowledgeChunk{int(time.time())}"`
     - Create Weaviate class: copy `KNOWLEDGE_CHUNK_CLASS` schema with new class name
     - Update `knowledge-shadow` alias to new class (delete existing alias if present, create pointing to new class)
     - Query `SELECT doc_id, s3_key, content_type, uploaded_by FROM documents WHERE status='indexed'`
     - For each doc: send SQS 1 message with `target_index=shadow` (include `job_id` from new `indexing_jobs` row)
     - Insert `indexing_jobs` row: `shadow_index=name`, `status='in_progress'`, `docs_total=N`, `initiated_by='admin'`, `reason=reason`
     - Return `{job_id, shadow_index, docs_queued, status}`
   - `async swap_index(session, weaviate_client, settings) -> dict`:
     - Query `indexing_jobs WHERE status='ready_to_swap' ORDER BY started_at DESC LIMIT 1`
     - If none: raise `HTTPException(409, "No index ready to swap — re-index may still be running")`
     - Update Weaviate `knowledge-live` alias to point to `shadow_index`
     - Execute `UPDATE indexing_jobs SET status='swapped', swapped_at=NOW() WHERE job_id=...`
     - Return `{job_id, swapped_to, status}`

3. Create `services/admin-service/src/dlq.py`:
   - `async inspect_dlq(sqs_client, dlq_url: str, max_messages: int = 10) -> dict`:
     - `receive_message(QueueUrl, MaxNumberOfMessages, VisibilityTimeout=0)` — peek without consuming
     - Parse `ApproximateReceiveCount` attribute for retry count
     - Return `{count, messages: [{message_id, body_preview, retries}]}`
   - `async requeue_messages(sqs_client, dlq_url: str, main_queue_url: str, message_ids: list[str]) -> dict`:
     - For each message_id: receive from DLQ, send to main queue, delete from DLQ
     - Accumulate counts of `requeued` and `failed`
     - Return `{requeued, failed}`

4. Update `services/admin-service/src/main.py`:
   - Wire all real handlers via `Depends()` for DB, SQS, Weaviate, httpx
   - Add `POST /api/v1/admin/swap-index` endpoint (not in current stub, required by spec)
   - Wire `GET /health`, `POST /admin/reindex`, `POST /admin/swap-index`, `GET /admin/dlq`, `POST /admin/dlq/requeue`
   - Remove all `stub: True` response fields

5. Extend `services/indexing-service/src/coordinator.py`:
   - Add `async maybe_complete_indexing_job(session: AsyncSession, doc_id: str) -> bool`:
     - Query `SELECT target_index FROM documents WHERE doc_id=:doc_id`
     - If `target_index != 'shadow'`: return False (live-index docs don't affect job tracking)
     - Find active job: `SELECT job_id, docs_total, docs_completed FROM indexing_jobs WHERE status='in_progress' LIMIT 1`
     - If none found: return False
     - `UPDATE indexing_jobs SET docs_completed = docs_completed + 1 WHERE job_id=:job_id`
     - If new `docs_completed == docs_total`: `UPDATE indexing_jobs SET status='ready_to_swap'`
     - Return True if job advanced to `ready_to_swap`
   - Call `maybe_complete_indexing_job` from main indexing loop after `maybe_complete_document` returns True

6. Unit tests — `services/admin-service/tests/`:
   - `conftest.py` — shared fixtures: mocked httpx client, mocked boto3 SQS, mocked Weaviate client, mocked PG session
   - `test_health.py` — test fully healthy response; test partial degraded (one service down); test Weaviate down
   - `test_reindex.py` — assert shadow class created; assert SQS 1 receives N messages; assert `indexing_jobs` row inserted
   - `test_swap.py` — assert alias update called; assert `indexing_jobs` marked `swapped`; test 409 when no `ready_to_swap` job exists
   - `test_dlq.py` — mock boto3 receive/send/delete; assert `requeued` count matches; test partial failure

---

## Group 2 — LLM Router Circuit Breaker Integration

**Parallel with Group 1.**
**Dependencies**: Group 0 complete (`circuit_breaker.py` written)
**Commit**: `feat(llm-router): integrate circuit breaker into LLM client`

### Tasks

1. Update `shared/clients/llm_client.py`:
   - Import `_llm_circuit_breaker` from `shared.llm_router.circuit_breaker`
   - In `stream_completion`:
     - Before calling primary: `if not _llm_circuit_breaker.is_available()` → skip to fallback
     - Wrap primary provider call in `asyncio.wait_for(..., timeout=5.0)`
     - On primary success (first token received or stream complete): call `_llm_circuit_breaker.record_success()`
     - On `asyncio.TimeoutError` or any exception from primary: call `_llm_circuit_breaker.record_failure()`; log circuit state; fall through to fallback
   - Log circuit state transitions at INFO level: `"Circuit breaker state: {old} → {new}"`

2. Unit tests `tests/test_circuit_breaker.py`:
   - `test_initial_state_is_closed` — new `CircuitBreaker()` starts CLOSED
   - `test_closed_to_open_on_failure_threshold` — fail 3× → assert state = OPEN
   - `test_open_returns_unavailable` — state = OPEN → `is_available()` returns False
   - `test_open_transitions_to_half_open_after_reset_timeout` — advance `time.monotonic` mock by 61s → `is_available()` returns True, state = HALF_OPEN
   - `test_half_open_success_closes_circuit` — HALF_OPEN + `record_success()` → state = CLOSED, `failure_count = 0`
   - `test_half_open_failure_reopens_circuit` — HALF_OPEN + `record_failure()` → state = OPEN
   - `test_stream_completion_skips_primary_when_open` — mock circuit OPEN → assert primary provider fn never called, fallback called
   - `test_timeout_triggers_failure` — mock primary to hang >5s → `TimeoutError` → `record_failure` called

---

## Group 3 — Zero-Downtime Re-index Integration Test

**Sequential.** After Groups 1 + 2 complete.
**Dependencies**: Real admin endpoints, extended Coordinator
**Commit**: `test(admin): zero-downtime re-index end-to-end integration test`

### Tasks

1. Create `tests/integration/test_reindex_e2e.py`:
   - Use `EMBEDDING_PROVIDER=mock` and `LLM_PRIMARY=mock` to avoid API calls
   - **Fixtures**: async PG session (test DB), mock Weaviate client, mock SQS client
   - **Setup**: insert 2 `documents` rows at `status=indexed` in PG; insert 2 `KnowledgeChunk` objects in Weaviate mock under `knowledge-live`
   - **Step 1 — Trigger reindex**: call `trigger_reindex(reason="test", ...)` directly; assert `indexing_jobs` row created with `status=in_progress` and `docs_total=2`; assert SQS 1 mock received 2 messages with `target_index=shadow`
   - **Step 2 — Simulate indexing**: for each queued doc, call `maybe_complete_document(...)` then `maybe_complete_indexing_job(...)` directly
   - **Step 3 — Ready to swap**: after both docs processed, assert `indexing_jobs.status = ready_to_swap`
   - **Step 4 — Swap index**: call `swap_index(...)` directly; assert Weaviate alias update was called with shadow class name; assert `indexing_jobs.status = swapped`

---

## Group 4 — Verification

**Sequential.** Last group.
**Dependencies**: Group 3 complete
**Commit**: `chore: Phase 3 verification — all checks green`

### Tasks

1. `ruff check services/ shared/ tests/` — must exit 0; fix any issues
2. `mypy shared/ --ignore-missing-imports` — must exit 0; fix any issues
3. `pytest services/ shared/ tests/ -v` — all tests must pass; fix any failures
4. `docker compose up -d` followed by `docker compose ps` — all containers show healthy
5. Smoke test: `curl http://localhost:{admin_port}/api/v1/health` → `status: healthy`, no `stub` fields in response
