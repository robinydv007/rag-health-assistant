# ADR 0004 — Shadow Index + Alias Swap for Zero-Downtime Re-Indexing

> **Status**: accepted
> **Date**: 2026-05-12
> **Supersedes**: N/A

## Context

The knowledge base needs to be updated periodically:
- New documents are added (ongoing, via Uploader — handled by normal pipeline)
- The embedding model is upgraded — requires re-vectorizing every document
- Chunk parameters change (size, overlap) — requires re-chunking every document
- Bulk policy or guideline updates — 100s of documents at once

A full re-index can take hours (vectorizing thousands of documents on GPU). If the system deletes the current index and rebuilds it, users have no search capability for the duration — potentially hours.

The p99.9% uptime target makes any planned maintenance window unacceptable.

## Decision

Use a shadow index + alias swap pattern:

1. Admin creates a new Weaviate index `knowledge-v{N+1}` (the "shadow" index). The current live index `knowledge-v{N}` is untouched.
2. Admin pushes all existing document S3 paths to SQS 1 with flag `target_index=shadow`.
3. The normal ingestion pipeline runs. Indexing Service writes to the shadow index only.
4. Chat Service always reads from the `knowledge-live` alias — it continues reading from the current live index throughout.
5. Indexing Coordinator tracks completion. When all chunks for all documents are indexed into the shadow, it signals Admin.
6. Admin swaps the `knowledge-live` alias to point to `knowledge-v{N+1}`. This is an atomic operation at the vector DB level.
7. Chat Service is now reading from the new index — no restart, no query interruption.
8. Old index `knowledge-v{N}` is retained for 24 hours for rollback, then deleted.

## Consequences

### Positive
- Zero query downtime during re-index — users are unaffected
- Clean rollback path: if new index has quality issues, swap alias back to old index
- Re-index can happen at any time — no maintenance window coordination needed
- Old and new index can be quality-checked before the swap

### Negative
- Storage cost: during re-index, two full indexes exist simultaneously (2× vector storage)
- Re-index duration: full pipeline runs again for all documents — could be hours; no SLA on completion
- Operator discipline required: must monitor Indexing Coordinator and confirm quality before triggering alias swap

### Risks
- New documents uploaded during re-index: they go into the live index (normal pipeline). When re-index completes and alias swaps, those new docs may not be in the shadow index. Mitigation: after swap, run a delta ingest of any docs uploaded during the re-index window.
- Index schema incompatibility: if re-index is triggered by a schema change, the alias swap may fail if old clients hold cached schema. Mitigation: schema changes require a restart of Chat Service after swap.

## Alternatives Considered

| Option | Why Rejected |
|--------|-------------|
| Delete + rebuild | Zero query availability during rebuild — unacceptable for 99.9% uptime |
| Incremental update (write to live) | Partial state during update — users see inconsistent results (some old chunks, some new); no rollback path |
| Read from both indexes during transition | Complex query logic; results are harder to rank across two indexes; adds latency |
| Blue/green at the service level | More infrastructure (2× ECS services); slower to switch; alias swap is simpler and sufficient |
