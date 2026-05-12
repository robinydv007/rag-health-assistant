import uuid
from datetime import datetime

from pydantic import BaseModel


class SourceCitation(BaseModel):
    doc_id: str
    title: str
    page: int | None = None
    chunk: str | None = None


class QueryRecord(BaseModel):
    query_id: uuid.UUID
    user_id: str
    session_id: str | None = None
    question: str
    response: str
    sources: list[SourceCitation] = []
    model_used: str
    latency_ms: int | None = None
    tokens_used: int | None = None
    index_queried: str = "live"
    pii_detected: bool = False
    created_at: datetime


class AskRequest(BaseModel):
    question: str
    user_id: str
    session_id: str | None = None
