# Backlog

> **Last Updated**: 2026-05-12

---

## Priority Levels

| Level | Meaning |
|-------|---------|
| **P0** | Critical — blocks current phase |
| **P1** | High — address in current/next phase |
| **P2** | Medium — within 2 phases |
| **P3** | Low — nice to have |

**Status**: `open` | `in-progress` | `resolved` | `deferred` | `deprecated`

---

## Bugs

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| _(none)_ | | | | | |

---

## Features

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| FEAT-001 | Shared Pydantic models and SQS message schemas | P0 | open | 0 | contracts/models |
| FEAT-002 | PostgreSQL schema + Alembic migrations | P0 | open | 0 | data-model |
| FEAT-003 | docker-compose local dev environment | P0 | open | 0 | devex |
| FEAT-004 | GitHub Actions CI pipeline | P0 | open | 0 | ci |
| FEAT-005 | Chat Service — query expand + hybrid search + SSE stream | P1 | open | 1 | chat |
| FEAT-006 | Uploader Service — S3 + PG + SQS 1 publish | P1 | open | 1 | uploader |
| FEAT-007 | Doc Processing — PII scrub + chunking + SQS 2 | P1 | open | 1 | doc-processing |
| FEAT-008 | Query audit log to PostgreSQL | P1 | open | 1 | compliance |
| FEAT-009 | Embedding Service — OpenAI text-embedding-3-large (3072-dim) batch processing | P1 | resolved | 2 | embedding |
| FEAT-010 | Indexing Service — Weaviate write + PG status update | P1 | resolved | 2 | indexing |
| FEAT-011 | Indexing Coordinator — chunk completion tracking | P1 | resolved | 2 | indexing |
| FEAT-012 | DLQ alerting via webhook/log (CloudWatch deferred to Phase 5) | P1 | resolved | 2 | ops |
| FEAT-013 | Admin Service — re-index trigger + alias swap | P1 | open | 3 | admin |
| FEAT-014 | LLM Router with circuit breaker + Llama fallback | P1 | open | 3 | chat |
| FEAT-015 | Zero-downtime re-index end-to-end test | P1 | open | 3 | admin |
| FEAT-016 | Prometheus metrics for all services | P2 | open | 4 | observability |
| FEAT-017 | Grafana dashboards (queue depth, p95 latency, LLM fallback rate) | P2 | open | 4 | observability |
| FEAT-018 | Jaeger distributed tracing | P2 | open | 4 | observability |
| FEAT-019 | ELK log aggregation | P2 | open | 4 | observability |
| FEAT-020 | Load test: 500 VU, p95 < 2s | P2 | open | 4 | performance |
| FEAT-021 | Chaos test: DLQ recovery when service crashes | P2 | open | 4 | resilience |
| FEAT-022 | HIPAA compliance audit (PII scan, audit log completeness) | P1 | open | 5 | compliance |
| FEAT-023 | AWS production CloudFormation / Terraform | P1 | open | 5 | infra |
| FEAT-024 | Operations runbooks | P2 | open | 5 | ops |
| FEAT-025 | Search relevance evaluation set | P2 | deferred | 3 | quality |

---

## Tech Debt

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| _(none yet)_ | | | | | |

---

## Enhancements

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| ENH-001 | Query caching layer (Redis) for repeated questions | P3 | open | 4 | performance |
| ENH-002 | Re-rank using cross-encoder (Cohere Rerank or local) | P3 | open | 2 | quality |
| ENH-003 | Document version management (track doc updates over time) | P3 | open | 3 | features |
| ENH-004 | Multi-language support for non-English clinical documents | P3 | open | 5 | features |
| ENH-005 | Web UI for clinical staff (React frontend) | P3 | open | 5 | features |
| ENH-006 | SSE streaming for /ask endpoint (token-by-token) | P3 | open | - | chat |
| ENH-007 | Local-dev no-API-key mock mode (MockEmbeddingClient + mock LLM) | P1 | resolved | 3 | devex |
