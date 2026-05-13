"""Shared settings module — each service imports and extends this base."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AWS
    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = None  # Set for local dev (ElasticMQ)

    # SQS
    sqs_queue_1_url: str = ""
    sqs_queue_2_url: str = ""
    sqs_queue_3_url: str = ""
    sqs_dlq_1_url: str = ""
    sqs_dlq_2_url: str = ""
    sqs_dlq_3_url: str = ""

    # S3 / MinIO
    s3_bucket: str = ""
    s3_raw_prefix: str = "raw-docs"
    s3_endpoint_url: str | None = None  # Set to http://minio:9000 for local dev
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"

    # PostgreSQL
    database_url: str = ""

    # Weaviate
    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: str | None = None

    # LLM
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_primary: str = "openai"       # Provider tried first — must be in registry
    llm_fallback: str = "anthropic"   # Provider used if primary fails
    llm_fallback_url: str | None = None  # Self-hosted Llama/Mistral endpoint (Phase 3)

    # Embedding — Phase 2: BiomedBERT via HF Inference API
    embedding_provider: str = "hf_inference"   # hf_inference | http_endpoint
    hf_inference_url: str = ""                 # HF feature-extraction pipeline URL
    hf_api_key: str = ""                       # HF token
    embedding_endpoint_url: str = ""           # Self-hosted GPU endpoint URL
    embedding_api_key: str | None = None       # Optional auth for self-hosted endpoint

    # DLQ alerting
    dlq_alert_webhook_url: str | None = None   # POST here when any DLQ depth > 0

    # Index
    live_index_alias: str = "knowledge-live"
    shadow_index_alias: str = "knowledge-shadow"
