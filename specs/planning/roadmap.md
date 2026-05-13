# Roadmap

> **Last Updated**: 2026-05-13

## Vision

A fully HIPAA-compliant RAG knowledge assistant that gives any healthcare staff member instant, source-cited answers from the organization's clinical document library — at scale, with zero downtime, and with every query audited.

---

## Release Plan

| Version | Phase | Key Deliverables | Target |
|---------|-------|-----------------|--------|
| v0.1.0 | Phase 0 — Bootstrap ✅ | Repo scaffold, contracts, local dev, CI pipeline | Sprint 1 |
| v0.2.0 | Phase 1 — Core Services ✅ | Chat + Uploader + Doc Processing end-to-end | Sprint 2–3 |
| v0.3.0 | Phase 2 — Embedding & Indexing ✅ | Full pipeline: embed → index, VectorDB queryable | Sprint 4–5 |
| v0.4.0 | Phase 3 — Admin & LLM Router | Admin ops, zero-downtime re-index, LLM fallback | Sprint 6 |
| v0.5.0 | Phase 4 — Observability & Hardening | Prometheus, Grafana, Jaeger, ELK, load testing | Sprint 7 |
| v1.0.0 | Phase 5 — Production | HIPAA audit, pen test, production deploy, runbooks | Sprint 8–9 |

---

## Phase Summaries

### Phase 0 — Bootstrap
**Goal**: Working local dev environment; all service skeletons; shared contracts locked; CI passing.

Deliverables:
- All 6 service directories with FastAPI/Python boilerplate
- Shared Pydantic models, SQS message schemas, config module
- `docker-compose.yml` bringing all services + Weaviate + PostgreSQL up
- GitHub Actions: lint (ruff), type check (mypy), test (pytest) on every PR
- 4+ ADRs written for core design decisions

**Does NOT include**: Real LLM calls, real AWS infrastructure, actual embeddings.

---

### Phase 1 — Core Services
**Goal**: A user can ask a question and get an answer; a user can upload a document and see it enter the pipeline.

Deliverables:
- Chat Service: query expand → hybrid search → rerank → LLM call → JSON response
- Uploader Service: file upload → S3 → PostgreSQL → SQS 1 publish
- Doc Processing: SQS 1 consumer → PII scrub → chunk → SQS 2 publish
- Query audit log writing to PostgreSQL
- Integration tests for each service

**Does NOT include**: Real GPU embeddings (use placeholder vectors), production AWS infra.

---

### Phase 2 — Embedding & Indexing ✅ (v0.3.0)
**Goal**: The full document pipeline runs end-to-end with real embeddings stored in Weaviate.

Deliverables:
- Embedding Service: OpenAI `text-embedding-3-large` (3072-dim), batch processing via `EmbeddingClient` abstraction
- Indexing Service: SQS 3 consumer → Weaviate `KnowledgeChunk` write + `chunk_audit` + PG status update
- Indexing Coordinator: chunk completion tracking (`chunks_indexed == chunks_total` → `status=indexed`)
- DLQ monitor: depth check + log WARNING + optional HTTP webhook (`DLQ_ALERT_WEBHOOK_URL`); CloudWatch deferred to Phase 5
- End-to-end pipeline verified: upload PDF → `status=indexed` + Weaviate queryable + `/ask` returns relevant chunks

---

### Phase 3 — Admin & LLM Router
**Goal**: Operations team can manage the knowledge base; system survives LLM provider outage.

Deliverables:
- Admin Service: re-index trigger, alias swap, DLQ view/requeue, health check
- Zero-downtime re-index flow fully tested
- LLM Router with circuit breaker (GPT-4/Claude → Llama 2/Mistral fallback)
- Load test: 500 concurrent users, p95 < 2s

---

### Phase 4 — Observability & Hardening
**Goal**: Production-grade visibility and resilience verified.

Deliverables:
- Prometheus metrics across all services
- Grafana dashboards: queue depth, p95 latency, error rate, LLM fallback rate
- Jaeger distributed tracing end-to-end
- ELK log aggregation
- Chaos testing: kill each service, verify DLQ recovery
- SLI/SLO definitions and alerting rules

---

### Phase 5 — Production
**Goal**: System is live, HIPAA-compliant, and operations team is equipped to run it.

Deliverables:
- HIPAA compliance audit (PII scrubbing verification, audit log completeness)
- Penetration test on API Gateway + auth
- AWS production environment provisioned (CloudFormation / Terraform)
- Runbooks: re-index, DLQ recovery, LLM fallback, rollback procedure
- On-call playbook and alerting escalation
- v1.0.0 release

---

## Guiding Principles

1. Ship working software in every phase — each phase release must be deployable
2. Each phase leaves the project in a releasable state with real value
3. Defer scope, not quality — cut features before cutting correctness or compliance
4. PII/PHI compliance is non-negotiable at every phase
