# Project Status

> **Last Updated**: 2026-05-13
> **Current Phase**: Phase 2 — Embedding & Indexing (`complete`)
> **Latest Release**: v0.2.0 (Phase 1 complete) — Phase 2 pending merge + tag
> **Health**: On Track

## Summary

The RAG Healthcare Knowledge Assistant is an internal AI system that allows healthcare staff to ask natural-language questions and receive accurate, source-cited answers from the organization's clinical document library (clinical guidelines, hospital policies, HL7 standards, drug formularies). Built on a 6-service microservices architecture on AWS with a 3-stage async document processing pipeline. HIPAA-compliant with automatic PII/PHI scrubbing, full query audit logging, and zero-downtime knowledge base updates.

## Completed Phases

| Phase | Name | Status | Released |
|-------|------|--------|---------|
| 0 | Bootstrap | Complete | v0.1.0 |
| 1 | Core Services | Complete | v0.2.0 |
| 2 | Embedding & Indexing | Complete | pending v0.3.0 |

## Active Phase

_(none — Phase 2 complete, awaiting `/complete-phase` and merge to main)_

## Upcoming Phases

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|-----------------|
| 3 | Admin & LLM Router | Planned | Zero-downtime re-index, LLM fallback |
| 4 | Observability & Hardening | Planned | Prometheus, Grafana, Jaeger, load test |
| 5 | Production | Planned | HIPAA audit, pen test, production deploy |

## Blockers

| ID | Description | Severity |
|----|-------------|----------|
| _(none)_ | | |

## Critical Items (P0)

| ID | Type | Description |
|----|------|-------------|
| _(none)_ | | |

## Next Actions

1. Run `/complete-phase` to finalize Phase 2 (sync-docs + tag v0.3.0)
2. Merge `phase-2-embedding-indexing` → `main`
3. Start Phase 3 — Admin & LLM Router

## Key Decisions Made

| ADR | Decision | Date |
|-----|----------|------|
| [0001](decisions/0001-microservices-over-monolith.md) | Microservices — one service per pipeline stage | 2026-05-12 |
| [0002](decisions/0002-sqs-async-pipeline.md) | SQS async pipeline with DLQs for document processing | 2026-05-12 |
| [0003](decisions/0003-medical-embedding-models.md) | BioGPT/SciBERT for domain-specific medical embeddings | 2026-05-12 |
| [0003a](decisions/0003a-biomedbert-hf-inference-api.md) | OpenAI text-embedding-3-large replaces HF BiomedBERT (not production-ready) | 2026-05-13 |
| [0004](decisions/0004-zero-downtime-reindex.md) | Shadow index + alias swap for zero-downtime re-indexing | 2026-05-12 |
| [0005](decisions/0005-ecs-fargate-over-eks.md) | ECS Fargate over EKS for container orchestration | 2026-05-12 |
| [0006](decisions/0006-vector-db-weaviate.md) | Weaviate for vector DB — hybrid search, self-hosted, alias swap | 2026-05-12 |
| [0007](decisions/0007-fastapi-backend-framework.md) | FastAPI for all HTTP-facing services — async SSE, Pydantic integration | 2026-05-12 |

## Recent Changes

- 2026-05-12: Project initialized — spec structure scaffolded from architecture design
- 2026-05-12: All vision docs, architecture specs, roadmap, and Phase 0 plan created
- 2026-05-12: CLAUDE.md and agent rules written
- 2026-05-12: Phase 0 complete — shared models, Alembic migrations, 6 service skeletons, Dockerfiles, docker-compose, init services, unit tests, GitHub Actions CI
- 2026-05-13: Phase 1 — Core Services started; branch `phase-1-core-services` created
- 2026-05-13: v0.2.0 released — Phase 1 complete: Uploader, Doc Processing, Chat Service end-to-end; 78 unit tests; full Docker stack verified
- 2026-05-13: Phase 2 — Embedding & Indexing complete: Embedding Service, Indexing Service, DLQ monitor, OpenAI text-embedding-3-large (3072-dim), 57 unit tests, all services healthy
