"""Unit tests for shared config module."""

from shared.config.settings import BaseServiceSettings
from shared.config.weaviate_schema import KNOWLEDGE_CHUNK_CLASS, WEAVIATE_SCHEMA


def test_base_settings_defaults():
    settings = BaseServiceSettings()
    assert settings.aws_region == "us-east-1"
    assert settings.weaviate_url == "http://localhost:8080"
    assert settings.embedding_model == "biogpt"
    assert settings.live_index_alias == "knowledge-live"
    assert settings.shadow_index_alias == "knowledge-shadow"
    assert settings.s3_raw_prefix == "raw-docs"


def test_base_settings_optional_fields_are_nullable():
    settings = BaseServiceSettings()
    # These are str | None — actual value depends on .env; just verify the type contract
    for field in ("aws_endpoint_url", "weaviate_api_key", "openai_api_key", "anthropic_api_key", "llm_fallback_url"):
        val = getattr(settings, field)
        assert val is None or isinstance(val, str), f"{field} must be str | None"


def test_weaviate_chunk_class_structure():
    assert KNOWLEDGE_CHUNK_CLASS["class"] == "KnowledgeChunk"
    assert KNOWLEDGE_CHUNK_CLASS["vectorizer"] == "none"
    prop_names = {p["name"] for p in KNOWLEDGE_CHUNK_CLASS["properties"]}
    expected = {"docId", "chunkId", "chunkIdx", "text", "docType", "title", "pageNum", "version", "embeddedModel", "indexedAt"}
    assert expected == prop_names


def test_weaviate_schema_wrapper():
    assert "classes" in WEAVIATE_SCHEMA
    assert len(WEAVIATE_SCHEMA["classes"]) == 1
    assert WEAVIATE_SCHEMA["classes"][0]["class"] == "KnowledgeChunk"
