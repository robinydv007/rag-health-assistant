# Project Status

> **Last Updated**: 2026-05-12
> **Current Phase**: Phase 0 — Bootstrap (`in progress`)
> **Latest Release**: None
> **Health**: On Track

## Summary

The RAG Healthcare Knowledge Assistant is an internal AI system that allows healthcare staff to ask natural-language questions and receive accurate, source-cited answers from the organization's clinical document library (clinical guidelines, hospital policies, HL7 standards, drug formularies). Built on a 6-service microservices architecture on AWS with a 3-stage async document processing pipeline. HIPAA-compliant with automatic PII/PHI scrubbing, full query audit logging, and zero-downtime knowledge base updates.

## Completed Phases

| Phase | Name | Status | Released |
|-------|------|--------|---------|
| _(none yet)_ | | | |

## Active Phase

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 0 | Bootstrap | In Progress | 31% |

**Phase 0 Goal**: Working local dev environment, all service skeletons, shared contracts locked, CI pipeline passing.

**Phase 0 Key Tasks** (see [tasks.md](phases/phase-0-bootstrap/tasks.md)):
- Group 0: Shared contracts (Pydantic models, SQS schemas, DB migrations)
- Group 1: Service skeletons (6 FastAPI apps with `/health` endpoints)
- Group 2: Docker & local dev (docker-compose with all services)
- Group 3: ADRs & spec documents
- Group 4: Wiring & integration
- Group 5: CI pipeline (GitHub Actions)

## Upcoming Phases

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|-----------------|
| 1 | Core Services | Planned | Chat + Uploader + Doc Processing end-to-end |
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

1. Complete Group 0: define shared Pydantic models + SQS message schemas + Alembic migrations
2. Complete Group 1: add `/ask`, `/ingest`, `/admin/reindex` stubs; wire shared config into services
3. Complete Group 2: write Dockerfiles for all 6 services + init scripts

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
