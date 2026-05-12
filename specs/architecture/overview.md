# Architecture Overview

> **Version**: 1.0  
> **Type**: Monorepo — 6 microservices + shared libraries + infrastructure  
> **Last Updated**: 2026-05-12

---

## System Summary

The RAG Healthcare Knowledge Assistant is an internal AI system that allows healthcare staff to ask natural-language medical questions and receive accurate, source-cited answers from the organization's own clinical document library.

The system processes uploaded documents through a 3-stage async pipeline, stores vector embeddings for semantic search, and uses a hybrid retrieval + LLM approach to generate responses. All patient data (PII/PHI) is scrubbed before content enters the knowledge base.

---

## High-Level Architecture

```
                      [ Users ]
                          |
                  [ AWS API Gateway ]
                JWT · Rate Limit · Route
              /           |             \
             /            |              \
  [ Chat Service ]  [ Uploader Service ]  [ Admin Service ]
  query expand       file → S3              reindex
  hybrid search      DB entry               alias swap
  rerank + LLM       push SQS 1             DLQ mgmt
  stream response         |
       |             [ SQS 1 ] ←— DLQ 1
       |                  |
       |        [ Doc Processing ]
       |        PII scrub · chunk
       |        tag metadata
       |                  |
       |             [ SQS 2 ] ←— DLQ 2
       |                  |
       |        [ Embedding Service ]
       |        BioGPT / SciBERT (GPU)
       |        EC2 GPU instance
       |                  |
       |             [ SQS 3 ] ←— DLQ 3
       |                  |
       |        [ Indexing Service ]        [ Indexing Coordinator ]
       |        write vectors                track chunk completion
       |        update PG status   ————————> signal admin when done
       |
  ─────────────────────────────────────
  [ Vector DB ]  [ PostgreSQL ]  [ S3 ]
  embeddings     audit logs       raw docs
  HA replica     query history    lifecycle
  ─────────────────────────────────────
            [ LLM Router ]
       GPT-4/Claude → Llama fallback

  ─────────────────────────────────────
            [ Observability ]
   Prometheus · Grafana · Jaeger · ELK
  ─────────────────────────────────────
```

---

## Services

| Service | Path | Responsibility | Trigger |
|---------|------|---------------|---------|
| Chat Service | `services/chat-service/` | Query expand → hybrid search → rerank → LLM → stream | HTTP POST (user) |
| Uploader Service | `services/uploader-service/` | S3 upload, PG record, SQS 1 publish | HTTP POST (user) |
| Doc Processing | `services/doc-processing/` | PII scrub, parse, chunk, push SQS 2 | SQS 1 consumer |
| Embedding Service | `services/embedding-service/` | BioGPT/SciBERT vectorization, push SQS 3 | SQS 2 consumer |
| Indexing Service | `services/indexing-service/` | Write vectors to VectorDB, update PG status | SQS 3 consumer |
| Admin Service | `services/admin-service/` | Re-index, alias swap, DLQ management, health | HTTP (ops only) |

---

## Async Pipeline

```
Uploader → SQS 1 → Doc Processing → SQS 2 → Embedding → SQS 3 → Indexing Service
```

- Each queue has a Dead Letter Queue (DLQ). Messages fail after 3 retries → DLQ → alert.
- Visibility timeout set per-stage to prevent message re-processing on pod crash.
- Queue depth drives auto-scaling for Doc Processing, Embedding, and Indexing services.

---

## Data Stores

| Store | Technology | Purpose |
|-------|-----------|---------|
| Vector DB | Weaviate (primary) / pgvector (fallback) | Chunk embeddings, semantic + keyword search |
| SQL | PostgreSQL (AWS RDS Multi-AZ) | Document status, query history, audit logs |
| Object Store | AWS S3 | Raw document storage, lifecycle policies |

---

## Zero-Downtime Re-Index Flow

1. `POST /admin/reindex` — Admin creates shadow index `v{N+1}`, marks all docs pending.
2. Admin pushes all S3 doc paths to SQS 1 with flag `target_index=shadow`.
3. Normal pipeline runs; Indexing Service writes to shadow index only.
4. Indexing Coordinator signals admin when all chunks written.
5. Admin swaps `index-live` alias to new index.
6. Old index retained 24h for rollback, then deleted.

---

## LLM Strategy

| Tier | Model | Condition |
|------|-------|-----------|
| Primary | GPT-4 / Claude 3 | Normal operation |
| Fallback | Llama 2 / Mistral 7B (self-hosted) | Primary unavailable or circuit open |

Circuit breaker opens after 3 consecutive failures or >5s latency threshold.

---

## Infrastructure

| Component | Technology |
|-----------|-----------|
| API Gateway | AWS API Gateway + Lambda Authorizer (JWT) |
| Compute | AWS ECS Fargate (all services except GPU) |
| GPU Compute | EC2 GPU instance (Embedding Service) |
| Queues | AWS SQS (3 queues + 3 DLQs) |
| CI/CD | GitHub Actions |
| Secrets | AWS Secrets Manager |
| Monitoring | Prometheus + Grafana, Jaeger, ELK |

---

## Key Architecture Decisions

See ADRs in `specs/decisions/`:

| ADR | Decision |
|-----|----------|
| [0001](../decisions/0001-microservices-over-monolith.md) | Microservices architecture with one-job-per-service |
| [0002](../decisions/0002-sqs-async-pipeline.md) | SQS-driven async pipeline for document processing |
| [0003](../decisions/0003-medical-embedding-models.md) | BioGPT/SciBERT for domain-specific embeddings |
| [0004](../decisions/0004-zero-downtime-reindex.md) | Shadow index + alias swap for zero-downtime re-indexing |
| [0005](../decisions/0005-ecs-fargate-over-eks.md) | ECS Fargate over EKS for orchestration |
