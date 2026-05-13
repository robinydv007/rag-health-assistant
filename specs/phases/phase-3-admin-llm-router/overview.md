# Phase 3 — Admin & LLM Router

> **Version**: 1.0
> **Status**: Not Started
> **Branch**: `phase-3-admin-llm-router`
> **Follows**: Phase 2 — Embedding & Indexing

---

## Goal

Operations team can manage the knowledge base without downtime; the system survives an LLM provider
outage. This phase moves the Admin Service from stubs to real implementations and adds a circuit
breaker to the LLM client — making both admin ops and LLM calls production-grade.

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM fallback provider | Anthropic (Claude) | Self-hosted Llama/Mistral deferred to Phase 5 with production infra. Anthropic already registered in `llm_client.py`. |
| Circuit breaker state store | In-memory per-process | No Redis needed for Phase 3; distributed state addressed in Phase 5. |
| Circuit breaker thresholds | 3 failures or >5s → OPEN; 60s → HALF_OPEN probe | Matches `specs/architecture/services.md#llm-router`. |
| Load test | Deferred to Phase 4 | Phase 4 adds Prometheus/Grafana — results are only actionable with metrics in place. |
| Search eval set (FEAT-025) | Deferred to Phase 4 | Phase 3 is already substantial; eval set pairs better with Phase 4 observability work. |
| HL7 parsing | Still deferred | Extensible parser dispatch table in doc-processing; no code change needed to add later. |
| Coordinator extension | Update `indexing_jobs` for shadow docs | When a shadow-targeted document reaches `indexed`, Coordinator increments `indexing_jobs.docs_completed`; signals `ready_to_swap` when `docs_completed == docs_total`. |

---

## Scope

### In Scope

- **Admin Service** (`services/admin-service/`): real implementations replacing all 5 stubs
  - `GET /api/v1/health` — aggregate health across all services, Weaviate, Postgres, SQS depths
  - `POST /api/v1/admin/reindex` — create Weaviate shadow class, set shadow alias, queue all indexed docs to SQS 1 with `target_index=shadow`, write `indexing_jobs` row
  - `POST /api/v1/admin/swap-index` — swap `knowledge-live` alias to shadow class; mark `indexing_jobs.status=swapped`
  - `GET /api/v1/admin/dlq` — inspect all 3 DLQs via boto3
  - `POST /api/v1/admin/dlq/requeue` — move DLQ messages back to main queues
- **Indexing Coordinator extension** (`services/indexing-service/src/coordinator.py`): update `indexing_jobs.docs_completed` for shadow-targeted documents; set `status=ready_to_swap` when complete
- **LLM Router circuit breaker** (`shared/llm_router/circuit_breaker.py`): `CircuitState` enum, `CircuitBreaker` class with CLOSED/OPEN/HALF_OPEN state machine
- **LLM client integration** (`shared/clients/llm_client.py`): integrate circuit breaker — 5s timeout, 3-failure OPEN threshold, 60s HALF_OPEN probe
- **Unit tests**: Admin Service endpoints (mocked deps), circuit breaker state machine
- **Zero-downtime re-index integration test**: end-to-end flow in mock mode

### Out of Scope

- Self-hosted Llama/Mistral fallback (Phase 5, with production infra)
- Load test: 500 VU, p95 < 2s (Phase 4, with observability)
- Search relevance evaluation set / FEAT-025 (Phase 4)
- HL7 parsing (still deferred)
- SSE streaming for `/ask` — ENH-006 (deferred)
- Cross-encoder reranking — ENH-002 (Phase 4+)
- Real AWS infrastructure (Phase 5)

---

## Deliverables

| Deliverable | Verification command |
|-------------|---------------------|
| `GET /health` returns real service statuses | `curl http://localhost:{admin_port}/api/v1/health` → JSON with live statuses, no stub fields |
| `POST /admin/reindex` creates shadow index | Weaviate contains new versioned class; `indexing_jobs` row with `status=in_progress` |
| `POST /admin/swap-index` updates live alias | Weaviate `knowledge-live` alias points to shadow class; `indexing_jobs.status=swapped` |
| `GET /admin/dlq` returns real DLQ depths | Response contains boto3-read counts (not hardcoded `0`) |
| `POST /admin/dlq/requeue` moves messages | Messages in main queue after requeue; DLQ count decreases |
| Circuit breaker OPEN after 3 failures | Unit test: mock OpenAI to fail 3× → state=OPEN → Anthropic called |
| Circuit breaker recovers HALF_OPEN→CLOSED | Unit test: advance time >60s → probe succeeds → state=CLOSED |
| Zero-downtime re-index test passes | `pytest tests/integration/test_reindex_e2e.py -v` exits 0 |
| All tests pass | `pytest services/ shared/ tests/ -v` exits 0 |
| Lint + type checks | `ruff check services/ shared/` and `mypy shared/ --ignore-missing-imports` exit 0 |

---

## Acceptance Criteria

1. `POST /admin/reindex` creates a new Weaviate class, sets `knowledge-shadow` alias to it, queries all `status=indexed` documents from Postgres, and pushes each as a SQS 1 message with `target_index=shadow`; returns 202 with `job_id`, `shadow_index`, and `docs_queued`
2. When all shadow-targeted documents reach `status=indexed` → `indexing_jobs.status=ready_to_swap`
3. `POST /admin/swap-index` updates the `knowledge-live` Weaviate alias to the shadow class and marks `indexing_jobs.status=swapped`
4. `GET /api/v1/health` returns live status from each service HTTP endpoint, Weaviate, Postgres, and all 3 SQS queue depths — never stub data
5. Circuit breaker trips (state=OPEN) after 3 consecutive OpenAI failures; subsequent calls route directly to Anthropic without attempting OpenAI
6. Circuit breaker enters HALF_OPEN after 60s, probes OpenAI once; success → CLOSED; failure → OPEN
7. Zero-downtime re-index integration test passes in mock mode: upload doc → index → trigger reindex → coordinator marks `ready_to_swap` → swap → verify `knowledge-live` alias points to new index
8. All unit tests and integration tests pass; ruff and mypy clean; Docker stack healthy
