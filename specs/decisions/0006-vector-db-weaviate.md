# ADR 0006 — Weaviate as Primary Vector Database

> **Status**: accepted
> **Date**: 2026-05-12
> **Supersedes**: N/A

## Context

The system requires a vector database to store and search chunk embeddings from healthcare documents. Queries use **hybrid retrieval** — a combination of dense semantic search (vector similarity) and sparse keyword search (BM25). This is critical in healthcare because:

- Clinical terms like drug names, ICD codes, and procedure names must match exactly → BM25 handles this.
- Conceptual or synonymous queries ("insulin dosing" → "glycaemic control protocol") need semantic search → vector similarity handles this.
- A vector DB that supports only one of the two forces us to run two separate systems, or lose recall on one dimension.

Additional constraints:
- **HIPAA**: patient data (after PII scrubbing) must stay within the organisation's cloud boundary. Fully managed external cloud services that store data on the provider's infrastructure are a compliance risk unless a BAA is in place.
- **Zero-downtime re-indexing**: the DB must support index aliases or multi-tenancy so we can swap a shadow index to live atomically.
- **Scale**: target 1000+ documents/min throughput during re-index; tens of millions of chunks at steady state.
- **Operational simplicity**: the team has Python/ML skills, not specialised vector DB ops experience.

## Decision

Use **Weaviate** as the primary vector database, deployed on AWS (self-hosted on ECS or EC2).

Use **pgvector** (PostgreSQL extension) as the fallback — already available on our RDS instance — for low-volume or degraded-mode queries if Weaviate is unavailable.

Weaviate is configured with:
- **Vectorizer**: `none` (we supply pre-computed BioGPT/SciBERT vectors from the Embedding Service)
- **Modules**: `bm25` for keyword search, `hybrid` query combining both modes
- **Index aliases**: `knowledge-live` and `knowledge-shadow` for zero-downtime swaps
- **Replication factor**: 2 (HA replica) on separate AZs

## Consequences

### Positive
- Native hybrid search (BM25 + vector) in a single query — no dual-system complexity
- Index alias support enables our zero-downtime re-index pattern (ADR-0004) without custom middleware
- Self-hosted on AWS keeps all data within our VPC — no data leaves the org boundary
- Python client (`weaviate-client`) integrates cleanly with FastAPI and LangChain
- Supports batched vector writes, which the Indexing Service uses for throughput

### Negative
- Self-hosted means we own availability, upgrades, and backup — Fargate task definitions + EBS snapshots required
- Weaviate's BM25 implementation is less mature than Elasticsearch's; acceptable for our query volume
- Schema migrations require index recreation; managed by the alias-swap pattern

### Risks
- If Weaviate proves operationally costly at scale, migration to a managed service (Pinecone, Qdrant Cloud) is possible — our Indexing Service writes through a thin abstraction layer, so swapping the DB requires only that layer and the query path in Chat Service to change.

## Alternatives Considered

| Option | Why Rejected |
|--------|-------------|
| **Pinecone** | Fully managed SaaS — data stored on Pinecone's infrastructure, not ours. No BAA available without enterprise contract. No native BM25; requires a separate keyword search layer. |
| **Qdrant** | Good hybrid search support, but alias/multi-tenancy for zero-downtime swaps is less mature. Smaller ecosystem; fewer LangChain integrations at time of decision. Self-hosted viable but fewer operational examples for AWS. |
| **Elasticsearch / OpenSearch (vector)** | Strong BM25 (it's the reference implementation), but vector search is a bolt-on — lower ANN performance than purpose-built vector DBs. Significantly more operational complexity and resource cost. OpenSearch on AWS is managed but heavier than needed. |
| **pgvector (primary)** | Already on our RDS instance — zero new infra. But: no native BM25 (would need `pg_search` or a separate FTS layer), limited to IVFFlat/HNSW indexes with modest scale, no alias support for zero-downtime swaps. Retained as fallback. |
| **Milvus** | Feature-rich and performant, but operationally the most complex option (Etcd + Pulsar dependencies). Overhead unjustified for this team size. |
