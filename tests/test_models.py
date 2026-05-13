"""Unit tests for shared Pydantic models."""

import uuid
from datetime import datetime, timezone

from shared.models.chunk import ChunkMetadata
from shared.models.document import DocType, DocumentCreate, DocumentRecord, DocumentStatus
from shared.models.messages import SQS1Message, SQS2Chunk, SQS2Message, SQS3Message
from shared.models.query import AskRequest, SourceCitation


def test_document_record_defaults():
    record = DocumentRecord(
        doc_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        title="Test Doc",
        doc_type=DocType.drug_formulary,
        s3_key="raw-docs/test/test.pdf",
        content_type="application/pdf",
        uploaded_by="user_123",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert record.status == DocumentStatus.pending
    assert record.target_index == "live"
    assert record.chunks_indexed == 0
    assert record.chunks_total is None


def test_document_create_auto_job_id():
    doc = DocumentCreate(
        title="Formulary 2025",
        doc_type=DocType.drug_formulary,
        s3_key="raw-docs/test/formulary.pdf",
        content_type="application/pdf",
        uploaded_by="usr_abc",
    )
    assert doc.target_index == "live"
    assert isinstance(doc.job_id, uuid.UUID)


def test_doc_type_enum_values():
    assert DocType.clinical_guideline == "clinical_guideline"
    assert DocType.hospital_policy == "hospital_policy"
    assert DocType.hl7_standard == "hl7_standard"
    assert DocType.drug_formulary == "drug_formulary"
    assert DocType.other == "other"


def test_document_status_progression():
    statuses = [s.value for s in DocumentStatus]
    assert "pending" in statuses
    assert "processing" in statuses
    assert "indexed" in statuses
    assert "failed" in statuses


def test_chunk_metadata_defaults():
    chunk = ChunkMetadata(
        doc_type=DocType.clinical_guideline,
        page_num=5,
        chunk_idx=2,
        version=1,
    )
    assert chunk.target_index == "live"


def test_sqs1_message_serialization():
    msg = SQS1Message(
        doc_id="doc_001",
        s3_key="raw-docs/doc_001/file.pdf",
        content_type="application/pdf",
        uploaded_by="usr_001",
        target_index="live",
        job_id="job_001",
        uploaded_at=datetime.now(timezone.utc),
    )
    data = msg.model_dump()
    assert data["doc_id"] == "doc_001"
    assert data["target_index"] == "live"


def test_sqs2_message_with_chunks():
    metadata = ChunkMetadata(doc_type=DocType.other, page_num=1, chunk_idx=0, version=1)
    chunk = SQS2Chunk(chunk_id="doc_001_chunk_000", text="Sample scrubbed text.", metadata=metadata)
    msg = SQS2Message(doc_id="doc_001", chunks=[chunk])
    assert len(msg.chunks) == 1
    assert msg.chunks[0].chunk_id == "doc_001_chunk_000"
    assert msg.chunks[0].metadata.target_index == "live"


def test_sqs3_message():
    metadata = ChunkMetadata(doc_type=DocType.other, page_num=1, chunk_idx=0, version=1)
    msg = SQS3Message(
        doc_id="doc_001",
        chunk_id="doc_001_chunk_000",
        text="Aspirin 325mg once daily for pain.",
        embedding=[0.123, -0.456, 0.789],
        metadata=metadata,
        target_index="live",
    )
    assert len(msg.embedding) == 3
    assert msg.target_index == "live"
    assert msg.text == "Aspirin 325mg once daily for pain."


def test_ask_request_optional_session():
    req = AskRequest(question="What is the insulin dosing?", user_id="usr_001")
    assert req.session_id is None


def test_ask_request_with_session():
    req = AskRequest(question="Dosing?", user_id="usr_001", session_id="sess_xyz")
    assert req.session_id == "sess_xyz"


def test_source_citation_optional_fields():
    citation = SourceCitation(doc_id="doc_001", title="Formulary 2025", page=42)
    assert citation.chunk is None
