# Project Charter

> **Project**: RAG Healthcare Knowledge Assistant
> **Created**: 2026-05-12
> **Version**: 1.0

## Problem Statement

Healthcare teams — clinical staff, care coordinators, and administrators — constantly need authoritative answers from a large and growing body of documents: clinical guidelines, hospital policies, HL7 standards, drug formularies, and EHR protocols. Finding the right information today means manually searching across disconnected document repositories, leading to delays, inconsistency, and the risk of acting on outdated guidance.

The core pain:
- **Too many documents, no unified search** — guidelines, policies, and standards live in different places with no single entry point.
- **Slow information retrieval** — manual searches take minutes; clinical decisions often can't wait.
- **Compliance exposure** — staff may use outdated versions of documents or skip verification entirely.
- **No audit trail** — there is no record of what information was consulted when a clinical decision was made.

## Solution

An internal AI knowledge assistant that lets healthcare staff ask natural-language questions and receive accurate, sourced answers — retrieved from the organization's own approved document library.

The system:
1. **Ingests** clinical documents (PDF, DOCX, TXT, EHR exports) into a searchable vector knowledge base.
2. **Answers** medical questions with hybrid semantic + keyword search, reranking, and LLM-generated responses with source citations.
3. **Scrubs PII/PHI** automatically from all ingested content before it enters the knowledge base.
4. **Audits** every query and response for compliance review.
5. **Scales** to 500+ concurrent users with sub-2-second p95 response times.
6. **Updates** the knowledge base with zero downtime using a shadow-index strategy.

Built on a 6-service microservices architecture on AWS (ECS Fargate), with a 3-stage async document processing pipeline (Doc Processing → Embedding → Indexing) and a dedicated Admin service for operations.

## Stakeholders

| Role | Name / Team | Responsibility |
|------|-------------|----------------|
| Product Owner | Healthcare IT / Clinical Informatics | Defines what documents go into the knowledge base; acceptance criteria |
| Technical Lead | Backend Engineering | Architecture decisions, service ownership |
| Primary Users | Clinical Staff (doctors, nurses, coordinators) | Ask medical questions, receive answers |
| Admin Users | Healthcare IT Ops | Upload documents, trigger re-indexing, monitor system health |
| Compliance | HIPAA Officer / Legal | Review audit logs, approve PII scrubbing approach |
| Infrastructure | Cloud/DevOps Team | AWS setup, CI/CD, monitoring |

## Scope

### In
- Natural-language Q&A over approved healthcare documents
- Document ingestion: PDF, DOCX, TXT, HL7/EHR formats
- Automated PII/PHI scrubbing at ingestion time
- Hybrid semantic + keyword search (Weaviate / pgvector)
- Medical-domain embeddings (BioGPT / SciBERT)
- LLM-generated answers with source citations (GPT-4 / Claude 3 primary; Llama 2 / Mistral fallback)
- Streaming responses via SSE
- Query audit logging to PostgreSQL
- Zero-downtime knowledge base updates (shadow index + alias swap)
- HIPAA-compliant architecture
- AWS-native infrastructure (API Gateway, ECS Fargate, SQS, S3, RDS)
- Observability: Prometheus + Grafana, Jaeger tracing, ELK stack

### Out
- Public-facing consumer health portal
- Real-time EHR data integration (live patient records)
- Custom model fine-tuning (use pre-trained medical models)
- Mobile native apps (web interface only in scope)
- Multi-tenant / multi-org support (single organization deployment)
- Automated document discovery / crawling (manual upload only)

## Success

This project succeeds when:
- Healthcare staff can get accurate, sourced answers to medical questions in under 2 seconds.
- The system supports 500+ concurrent users without degradation.
- All ingested documents are PII/PHI-free within the vector knowledge base.
- Every query is audit-logged with user, question, sources retrieved, and response.
- The knowledge base can be fully re-indexed with zero user-visible downtime.
- The system maintains 99.9% uptime across a rolling 30-day window.

See `success-criteria.md` for measurable targets.
