# Phase 3 History

> Append-only decision log. Format: `### [TYPE] YYYY-MM-DD — Title`

---

### [NOTE] 2026-05-13 — Phase 3 brainstormed; scope locked

Topics: phase-planning, scope, brainstorm
Affects-phases: phase-3-admin-llm-router
Affects-specs: specs/planning/roadmap.md, specs/phases/phase-3-admin-llm-router/overview.md
Detail: Phase 3 brainstormed via /brainstorm-phase immediately after Phase 2 completion (v0.3.0). No P0/P1 bugs in backlog — clean runway. Scope locked to Admin Service real implementations, LLM Router circuit breaker, and zero-downtime re-index integration test. Phase files written and committed.

---

### [DECISION] 2026-05-13 — LLM fallback set to Anthropic for Phase 3; self-hosted deferred to Phase 5

Topics: llm-router, circuit-breaker, fallback, anthropic, llama
Affects-phases: phase-3-admin-llm-router, phase-5-production
Affects-specs: specs/architecture/services.md#llm-router
Detail: The architecture spec names Llama 2/Mistral as the self-hosted fallback. Phase 3 uses the existing Anthropic provider (already registered in `llm_client.py`) as the fallback instead. Self-hosted Llama/Mistral requires a running model server and production-like infra — deferred to Phase 5. The architecture spec remains authoritative; this is a phase-scoped deviation, not an architecture change.

---

### [DECISION] 2026-05-13 — Circuit breaker state is in-memory per-process; no Redis

Topics: llm-router, circuit-breaker, state
Affects-phases: phase-3-admin-llm-router
Affects-specs: none
Detail: Circuit breaker state (`CircuitState`, `failure_count`, `last_failure_time`) lives in a module-level singleton in `shared/llm_router/circuit_breaker.py`. Per-process in-memory is acceptable for Phase 3 (single-replica dev/staging). Distributed state (Redis) is a Phase 5 concern when running multiple Chat Service replicas under load.

---

### [DECISION] 2026-05-13 — Load test (500 VU, p95 < 2s) deferred from Phase 3 to Phase 4

Topics: performance, load-test, observability
Affects-phases: phase-3-admin-llm-router, phase-4-observability-hardening
Affects-specs: specs/planning/roadmap.md
Detail: The roadmap listed a load test as a Phase 3 deliverable. Moved to Phase 4 where Prometheus metrics and Grafana dashboards provide the observability needed to interpret and act on results. Load test without metrics is noise.

---

### [DECISION] 2026-05-13 — FEAT-025 (search relevance eval set) deferred from Phase 3 to Phase 4

Topics: quality, evaluation, feat-025
Affects-phases: phase-3-admin-llm-router, phase-4-observability-hardening
Affects-specs: specs/backlog/backlog.md
Detail: FEAT-025 was already deferred from Phase 2 to Phase 3. Deferred again to Phase 4 — Phase 3 scope is already substantial (Admin Service + circuit breaker + re-index integration test). An eval set pairs better with Phase 4 observability work.

---

### [DECISION] 2026-05-13 — Indexing Coordinator extended to track indexing_jobs completion

Topics: indexing, coordinator, indexing-jobs, admin, zero-downtime-reindex
Affects-phases: phase-3-admin-llm-router
Affects-specs: specs/architecture/services.md#indexing-service
Detail: `coordinator.py` currently only updates `documents.status`. Phase 3 extends it with `maybe_complete_indexing_job()` — called after a document reaches `indexed` status. If the document had `target_index=shadow`, it increments `indexing_jobs.docs_completed` and transitions the job to `ready_to_swap` when `docs_completed == docs_total`. This is the signal that `POST /admin/swap-index` waits for.

---

### [NOTE] 2026-05-13 — Phase 3 officially started; branch created

Topics: phase-planning, git
Affects-phases: phase-3-admin-llm-router
Affects-specs: specs/status.md, specs/phases/README.md
Detail: Phase 3 started via `/start-phase`. Branch `phase-3-admin-llm-router` created from `main`. One open P1 bug (BUG-001 — indexing-service Weaviate startup crash) has an existing fix branch `fix/indexing-service-weaviate-startup`; will be merged into this branch before Group 0 implementation begins.

---
