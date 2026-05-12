# Project Status

> **Last Updated**: 2026-05-13
> **Current Phase**: Phase 1 — Core Services (`in-progress`)
> **Latest Release**: v0.1.0 (Phase 0 complete)
> **Health**: On Track

## Summary

The RAG Healthcare Knowledge Assistant is an internal AI system that allows healthcare staff to ask natural-language questions and receive accurate, source-cited answers from the organization's clinical document library (clinical guidelines, hospital policies, HL7 standards, drug formularies). Built on a 6-service microservices architecture on AWS with a 3-stage async document processing pipeline. HIPAA-compliant with automatic PII/PHI scrubbing, full query audit logging, and zero-downtime knowledge base updates.

## Completed Phases

| Phase | Name | Status | Released |
|-------|------|--------|---------|
| 0 | Bootstrap | Complete | v0.1.0 |

## Active Phase

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 1 | Core Services | In Progress | 0% |

**Phase 1 Goal**: Chat + Uploader + Doc Processing end-to-end — real document ingestion, text extraction, SQS pipeline wired.

## Upcoming Phases

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|-----------------|
| 2 | Embedding & Indexing | Planned | Full pipeline, VectorDB queryable |
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

1. Implement Group 0 — Infrastructure & Shared Prerequisites (MinIO, S3 client, LLM client, synonym dict)
2. Implement Group 1 — Uploader Service (`POST /api/v1/knowledge/ingest`)
3. Implement Group 2 — Doc Processing Service (SQS consumer, Presidio, parsers, chunker)
4. Implement Group 3 — Chat Service (`/ask`, `/history`, SSE stream, audit log)

## Key Decisions Made

| ADR | Decision | Date |
|-----|----------|------|
| [0001](decisions/0001-microservices-over-monolith.md) | Microservices — one service per pipeline stage | 2026-05-12 |
| [0002](decisions/0002-sqs-async-pipeline.md) | SQS async pipeline with DLQs for document processing | 2026-05-12 |
| [0003](decisions/0003-medical-embedding-models.md) | BioGPT/SciBERT for domain-specific medical embeddings | 2026-05-12 |
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
