# Phase 3 — Tasks

> **Status**: In Progress
> Legend: `[ ]` open · `[/]` in-progress · `[x]` done

---

## Group 0 — Circuit Breaker Types + Admin Service Deps
> Sequential — blocks all other groups

- [x] Create `shared/llm_router/__init__.py`
- [x] Create `shared/llm_router/circuit_breaker.py` — `CircuitState` enum, `CircuitBreaker` class with CLOSED/OPEN/HALF_OPEN state machine, module-level singleton
- [x] Add `httpx`, `weaviate-client` to `services/admin-service/requirements.txt`
- [x] Create `services/admin-service/src/deps.py` — `get_db()`, `get_sqs_client()`, `get_weaviate_client()`, `get_http_client()`
- [x] Create `services/admin-service/src/settings.py` — extend `BaseServiceSettings` with service URL env vars

---

## Group 1 — Admin Service Endpoints
> Parallel with Group 2

- [x] Create `services/admin-service/src/health.py` — `check_service`, `check_postgres`, `check_weaviate`, `get_sqs_depth`, `aggregate_health`
- [x] Create `services/admin-service/src/reindex.py` — `trigger_reindex` (shadow class + alias + SQS queue + indexing_jobs row), `swap_index` (alias swap + job status update)
- [x] Create `services/admin-service/src/dlq.py` — `inspect_dlq`, `requeue_messages`
- [x] Update `services/admin-service/src/main.py` — wire real handlers, add `POST /swap-index`, remove stub fields
- [x] Extend `services/indexing-service/src/coordinator.py` — add `maybe_complete_indexing_job`; call it from indexing loop after `maybe_complete_document` returns True
- [x] Create `services/admin-service/tests/conftest.py` — shared fixtures
- [x] Create `services/admin-service/tests/test_health.py`
- [x] Create `services/admin-service/tests/test_reindex.py`
- [x] Create `services/admin-service/tests/test_swap.py`
- [x] Create `services/admin-service/tests/test_dlq.py`

---

## Group 2 — LLM Router Circuit Breaker Integration
> Parallel with Group 1

- [x] Update `shared/clients/llm_client.py` — integrate `_llm_circuit_breaker` with `asyncio.wait_for` 5s timeout, `record_success/failure`, skip primary when OPEN
- [x] Create `tests/test_circuit_breaker.py` — 9 unit tests covering all state transitions and integration with stream_completion

---

## Group 3 — Zero-Downtime Re-index Integration Test
> Sequential — after Groups 1 + 2

- [x] Create `tests/integration/test_reindex_e2e.py` — 4-step end-to-end test: trigger → simulate indexing → verify ready_to_swap → swap → verify alias

---

## Group 4 — Verification
> Sequential — last

- [ ] `ruff check services/ shared/ tests/` exits 0
- [ ] `mypy shared/ --ignore-missing-imports` exits 0
- [ ] `pytest services/ shared/ tests/ -v` all pass
- [ ] `docker compose up -d && docker compose ps` — all containers healthy
- [ ] Smoke test: `curl .../api/v1/health` returns live data, no stub fields
