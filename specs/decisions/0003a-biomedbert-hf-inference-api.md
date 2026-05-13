# ADR 0003a — OpenAI text-embedding-3-large (Amendment to ADR 0003)

> **Status**: accepted
> **Date**: 2026-05-13
> **Amends**: [ADR 0003 — BioGPT/SciBERT for Domain-Specific Medical Embeddings](0003-medical-embedding-models.md)
> **Note**: Originally adopted BiomedBERT via HuggingFace Serverless API; HF was removed mid-phase (HTTP 400 errors, not production-ready). Final decision: OpenAI `text-embedding-3-large` (3072-dim).

## Context

ADR 0003 selected BioGPT (Microsoft) and SciBERT (AllenAI) deployed on EC2 GPU instances as the embedding models for the RAG pipeline. During Phase 2 planning, two problems with that decision were identified:

1. **Infrastructure complexity**: Provisioning, managing, and paying for EC2 GPU instances (g4dn.xlarge, ~$0.526/hr) is significant overhead for a development phase. Model download from S3, Docker-in-Docker GPU access, and CUDA version pinning all add friction before the first chunk is embedded.

2. **Model selection**: BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext (Microsoft) is trained on 14 million PubMed abstracts and full texts — a larger and more directly relevant corpus than BioGPT's pretraining data for the embedding use case. BiomedBERT also produces 768-dim contextual embeddings natively; BioGPT is a generative model adapted for embeddings, which adds inference complexity.

## Decision

**Replace self-hosted BioGPT/SciBERT on EC2 GPU with OpenAI `text-embedding-3-large` (3072-dim vectors).**

Originally planned as BiomedBERT via HuggingFace Serverless API, but HF produced persistent HTTP 400 errors and is not production-ready for embedding workloads. Switched to OpenAI `text-embedding-3-large` which is stable, production-grade, and delivers high-quality dense vectors.

The switch is implemented via a provider abstraction (`shared/clients/embedding_client.py`):

| `EMBEDDING_PROVIDER` | Implementation | When to use |
|---|---|---|
| `openai` (default) | `OpenAIEmbeddingClient` — calls OpenAI Embeddings API | Phase 2+ (default) |
| `http_endpoint` | `HTTPEndpointClient` — calls any HTTP model server | Self-hosted GPU (Triton, vLLM, custom FastAPI) |

Both clients produce `[[float, ...], ...]` vectors. Switching to self-hosted GPU in Phase 5 requires only an env var change — zero code changes in Embedding Service or Chat Service.

## Consequences

### Positive
- No EC2 GPU provisioning in Phase 2 — eliminates ~$0.526/hr and all CUDA/Docker overhead
- BiomedBERT is a stronger baseline for PubMed-style clinical text than BioGPT in embedding mode
- Provider abstraction makes the GPU switch mechanical at Phase 5 (env var only)
- HF Serverless API handles model loading, scaling, and hardware — no ops burden

### Negative
- HF Serverless Inference has rate limits on the free tier — not suitable for production throughput
- Cold-start 503 responses (model loading) require retry logic — implemented with up to 5 retries at 20s intervals
- Latency per batch is higher than a warm local GPU endpoint (~200–500ms per batch vs ~50ms)

### Changed from ADR 0003
- `EMBEDDING_MODEL=biogpt | scibert` env var replaced by `EMBEDDING_PROVIDER=openai | http_endpoint`
- EC2 GPU instance removed from infrastructure plan entirely
- S3 paths `models/biogpt/` and `models/scibert/` are now unused — not provisioned
- `HFInferenceClient` and all HF env vars (`HF_INFERENCE_URL`, `HF_API_KEY`) removed entirely
- Vector dimension changes from 768 (BiomedBERT) to 3072 (text-embedding-3-large)
- ADR 0003's "risks" around GPU spot interruption are eliminated

## Self-Hosted GPU Upgrade Path (Phase 5)

When production volume warrants moving off the OpenAI API:

1. Deploy a model server (e.g. `text-embeddings-inference` from HuggingFace, or a FastAPI wrapper around a transformer model)
2. Set `EMBEDDING_PROVIDER=http_endpoint` and `EMBEDDING_ENDPOINT_URL=http://your-gpu-server:8080/embed`
3. No code changes required in Embedding Service, Indexing Service, or Chat Service
