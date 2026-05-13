# Architecture Decision Records

> Significant decisions, their context, and the reasoning behind them.
> Every decision here has a "why" — not just a "what".

## Status Values

`proposed` | `accepted` | `superseded` | `deprecated`

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0000](0000-template.md) | ADR Template | — | — |
| [0001](0001-microservices-over-monolith.md) | Microservices architecture — one service per pipeline stage | accepted | 2026-05-12 |
| [0002](0002-sqs-async-pipeline.md) | SQS async pipeline with DLQs for document processing | accepted | 2026-05-12 |
| [0003](0003-medical-embedding-models.md) | BioGPT/SciBERT for domain-specific medical embeddings | accepted | 2026-05-12 |
| [0004](0004-zero-downtime-reindex.md) | Shadow index + alias swap for zero-downtime re-indexing | accepted | 2026-05-12 |
| [0005](0005-ecs-fargate-over-eks.md) | ECS Fargate over EKS for container orchestration | accepted | 2026-05-12 |
| [0006](0006-vector-db-weaviate.md) | Weaviate as primary vector database (hybrid search + alias swap) | accepted | 2026-05-12 |
| [0007](0007-fastapi-backend-framework.md) | FastAPI for all HTTP-facing services | accepted | 2026-05-12 |
| [0008](0008-ask-json-response-sse-deferred.md) | /ask returns JSON in Phase 1–2; SSE deferred to ENH-006 | accepted | 2026-05-13 |
