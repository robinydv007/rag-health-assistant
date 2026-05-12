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

    # S3
    s3_bucket: str = ""
    s3_raw_prefix: str = "raw-docs"

    # PostgreSQL
    database_url: str = ""

    # Weaviate
    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: str | None = None

    # LLM
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_fallback_url: str | None = None  # Self-hosted Llama/Mistral endpoint

    # Embedding
    embedding_model: str = "biogpt"  # biogpt | scibert

    # Index
    live_index_alias: str = "knowledge-live"
    shadow_index_alias: str = "knowledge-shadow"
