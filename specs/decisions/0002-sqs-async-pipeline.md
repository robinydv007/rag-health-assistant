# ADR 0002 — SQS Async Pipeline with DLQs for Document Processing

> **Status**: accepted
> **Date**: 2026-05-12
> **Supersedes**: N/A

## Context

The document processing pipeline (Uploader → Doc Processing → Embedding → Indexing) is a multi-stage transformation that is:

- **Long-running**: Processing a large PDF through PII scrubbing, chunking, GPU embedding, and DB writes can take minutes.
- **Failure-prone at each stage**: Malformed PDFs, model OOM errors, DB write failures — any stage can fail.
- **Variable load**: Operators may bulk-upload hundreds of documents at once; pipeline services need to absorb that spike without dropping work.

If services called each other directly (HTTP chain), a downstream failure would propagate back to the user upload. If Embedding crashes, the user's upload is lost. There is no natural retry.

Additionally, direct HTTP calls couple service availability — every service must be up for a document to flow through.

## Decision

Use AWS SQS as the communication layer between all pipeline stages:

```
Uploader → SQS 1 → Doc Processing → SQS 2 → Embedding → SQS 3 → Indexing
```

Each queue has a corresponding Dead Letter Queue (DLQ). Messages are retried 3 times; after 3 failures, the message moves to the DLQ and a CloudWatch alarm fires.

Queue depth (not CPU usage) is the auto-scaling signal for Doc Processing, Embedding, and Indexing services.

Visibility timeout per queue is set longer than the expected processing time for that stage to prevent duplicate processing when a pod crashes mid-job.

## Consequences

### Positive
- Each service can fail and restart without losing work — SQS retains messages
- Services scale based on actual work pending (queue depth), not a proxy metric (CPU)
- The Uploader returns HTTP 202 immediately — user gets a job ID without waiting for processing
- Pipeline stages are fully decoupled: upgrading or restarting the Embedding service doesn't affect Uploader or Chat

### Negative
- Processing is not real-time — there is no SLA on when a document becomes queryable (minutes to hours depending on queue depth)
- Debugging a failed message requires DLQ inspection (mitigated by CloudWatch alarms and the Admin DLQ API)
- Local development requires an SQS-compatible service (ElasticMQ in docker-compose)

### Risks
- Message ordering: SQS Standard queues do not guarantee ordering. For chunked documents, this is fine — each chunk is independent. If ordering matters in a future use case, switch to SQS FIFO.
- Message size: SQS max payload is 256KB. For large chunk batches, messages must stay under this limit (mitigated by chunking strategy and S3 pointer pattern if needed).

## Alternatives Considered

| Option | Why Rejected |
|--------|-------------|
| Direct HTTP service-to-service calls | No durability — downstream failure loses work; tight availability coupling |
| Kafka | Overkill for this throughput; requires cluster management; SQS is fully managed with DLQ built in |
| Step Functions | Good for orchestration, but adds cost and complexity for a straightforward linear pipeline |
| RabbitMQ | Self-managed; SQS is managed by AWS and integrates natively with CloudWatch and ECS autoscaling |
