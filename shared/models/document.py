import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DocType(str, Enum):
    clinical_guideline = "clinical_guideline"
    hospital_policy = "hospital_policy"
    hl7_standard = "hl7_standard"
    drug_formulary = "drug_formulary"
    other = "other"


class DocumentStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    embedding = "embedding"
    indexing = "indexing"
    indexed = "indexed"
    failed = "failed"


class DocumentRecord(BaseModel):
    doc_id: uuid.UUID
    job_id: uuid.UUID
    title: str
    doc_type: DocType
    s3_key: str
    content_type: str
    uploaded_by: str
    target_index: str = "live"
    status: DocumentStatus = DocumentStatus.pending
    chunks_total: int | None = None
    chunks_indexed: int = 0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentCreate(BaseModel):
    job_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    doc_type: DocType
    s3_key: str
    content_type: str
    uploaded_by: str
    target_index: str = "live"
