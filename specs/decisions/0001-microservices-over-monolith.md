# ADR 0001 — Microservices Architecture — One Service Per Pipeline Stage

> **Status**: accepted
> **Date**: 2026-05-12
> **Supersedes**: N/A

## Context

The system has two distinct workloads that have completely different performance characteristics:

1. **Real-time query path** (Chat Service): User-facing, latency-sensitive, needs to scale with active connections. p95 < 2 seconds is a hard requirement.

2. **Batch document processing pipeline** (Doc Processing → Embedding → Indexing): Throughput-sensitive, latency-tolerant, CPU/GPU-intensive, needs to scale independently based on queue depth.

If these workloads were coupled in a single application, scaling one would scale the other. Scaling the embedding GPU workers (expensive) to handle a document spike would also scale the user-facing query handler (unnecessary). The reverse is also true — a traffic spike on the query side would waste GPU compute.

Additionally, each pipeline stage has a different failure profile:
- Chat Service fails under high query load
- Embedding Service fails if the model runs out of GPU memory
- Doc Processing fails on malformed documents

Coupling them in a monolith means one stage's failure mode can crash the others.

## Decision

Build 6 separate services, each responsible for exactly one job. No service owns two pipeline stages. Services communicate via SQS queues (async) or HTTP (sync, user-facing only).

Services:
1. **Chat Service** — query answering only
2. **Uploader Service** — document intake only
3. **Doc Processing** — PII scrub + chunking only
4. **Embedding Service** — vectorization only
5. **Indexing Service** — vector DB writes only
6. **Admin Service** — operational tasks only (separate from user traffic)

## Consequences

### Positive
- Each service scales independently based on its own bottleneck (connections / queue depth / GPU load)
- One service crashing does not bring down the others — SQS queues buffer the work
- Each service is deployable independently with no coordination
- Teams can own individual services without stepping on each other

### Negative
- 6 separate codebases to lint, test, build, and deploy (mitigated by monorepo structure and shared CI)
- Distributed tracing required to follow a request across services (Jaeger)
- More operational complexity: 6 ECS task definitions, 3 SQS queues, 3 DLQs

### Risks
- Contract drift: if SQS message schemas change in one service without updating others, the pipeline breaks. Mitigated by shared Pydantic models in `shared/models/messages.py`.

## Alternatives Considered

| Option | Why Rejected |
|--------|-------------|
| Monolith with threading | Cannot scale GPU workers independently from API handlers; failure isolation is poor |
| 2 services (API + Pipeline) | Still conflates query latency with batch throughput on the pipeline side; embedding and indexing have different scaling needs |
| Lambda functions | Cold start latency incompatible with p95 < 2s for Chat Service; GPU workloads not supported |
