from datetime import datetime

from pydantic import BaseModel

from shared.models.chunk import ChunkMetadata


class SQS1Message(BaseModel):
    """Uploader → Doc Processing"""
    doc_id: str
    s3_key: str
    content_type: str
    uploaded_by: str
    target_index: str
    job_id: str
    uploaded_at: datetime


class SQS2Chunk(BaseModel):
    chunk_id: str
    text: str
    metadata: ChunkMetadata


class SQS2Message(BaseModel):
    """Doc Processing → Embedding Service"""
    doc_id: str
    chunks: list[SQS2Chunk]


class SQS3Message(BaseModel):
    """Embedding Service → Indexing Service"""
    doc_id: str
    chunk_id: str
    text: str           # Scrubbed chunk text — required for Weaviate hybrid search
    embedding: list[float]
    metadata: ChunkMetadata
    target_index: str
