# Success Criteria

> Measurable targets. When all are met, the project has achieved its goals.

## Phase 0 Targets (Bootstrap)

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Repo structure | All services scaffolded, CLAUDE.md, specs complete | Directory audit |
| Local dev environment | `docker-compose up` brings all services online | Manual smoke test |
| ADRs written | 4+ ADRs covering core design decisions | Count files in `specs/decisions/` |
| CI pipeline | GitHub Actions runs lint + tests on every PR | PR check status |
| Shared contracts | Pydantic models, config schema, SQS message schemas defined | Code review |

## Phase 1 Targets (Core Services)

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Chat service query | Returns answer with source citations | Integration test |
| Document upload | HTTP 202 returned, job ID valid, S3 write confirmed | Integration test |
| Doc processing | PII scrubbed, chunks created and pushed to SQS 2 | Unit + integration test |
| Audit log | Every query written to PostgreSQL `query_history` table | DB query |
| Streaming | First token arrives within 500ms | Load test |

## Phase 2 Targets (Embedding & Indexing)

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Embedding pipeline | Chunks converted to BioGPT/SciBERT vectors end-to-end | Integration test |
| Vector DB write | Vectors persisted in Weaviate, queryable | Manual query |
| Doc status tracking | PostgreSQL `documents` table reflects processing stages | DB query |
| DLQ alerting | Failed messages trigger CloudWatch alert within 5 min | Chaos test (kill a service) |

## Phase 3 Targets (Admin & LLM Router)

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Re-index flow | Full re-index with zero query downtime (alias swap) | Load test during re-index |
| LLM fallback | Circuit breaker switches to Llama within 30s of primary failure | Chaos test |
| DLQ management | Admin API can view and requeue failed messages | API test |
| Health endpoint | `/api/v1/health` reports all service statuses | Monitoring check |

## Long-Term / Production Targets

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Response time (p95) | < 2 seconds end-to-end | Load test (Locust/k6) with 500 VUs |
| Concurrent users | 500+ without error rate increase | Load test steady-state |
| Document throughput | 1,000+ documents processed per minute | Stress test SQS pipeline |
| Uptime (30-day) | ≥ 99.9% | CloudWatch availability metric |
| Re-index downtime | Zero seconds of query unavailability | Measured during alias swap |
| PII in knowledge base | Zero raw PII/PHI in vector DB or PostgreSQL query history | Security audit scan |
| Audit coverage | 100% of user queries logged with user ID, question, sources, response | DB completeness check |
| LLM fallback RTO | < 30 seconds to switch to fallback model | Circuit breaker test |
| Search relevance | > 80% of test questions return the correct source document in top 3 | Evaluation set (see `specs/benchmarks/`) |
