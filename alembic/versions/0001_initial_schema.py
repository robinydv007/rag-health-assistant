"""Initial schema: documents, query_history, indexing_jobs, chunk_audit

Revision ID: 0001
Revises:
Create Date: 2026-05-12
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            job_id          UUID NOT NULL,
            title           TEXT NOT NULL,
            doc_type        TEXT NOT NULL,
            s3_key          TEXT NOT NULL,
            content_type    TEXT NOT NULL,
            uploaded_by     TEXT NOT NULL,
            target_index    TEXT NOT NULL DEFAULT 'live',
            status          TEXT NOT NULL DEFAULT 'pending',
            chunks_total    INTEGER,
            chunks_indexed  INTEGER DEFAULT 0,
            error_message   TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            query_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         TEXT NOT NULL,
            session_id      TEXT,
            question        TEXT NOT NULL,
            response        TEXT NOT NULL,
            sources         JSONB NOT NULL DEFAULT '[]',
            model_used      TEXT NOT NULL,
            latency_ms      INTEGER,
            tokens_used     INTEGER,
            index_queried   TEXT NOT NULL DEFAULT 'live',
            pii_detected    BOOLEAN DEFAULT FALSE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_query_history_user_id ON query_history(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at DESC)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS indexing_jobs (
            job_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            shadow_index    TEXT NOT NULL,
            reason          TEXT,
            status          TEXT NOT NULL DEFAULT 'in_progress',
            docs_total      INTEGER NOT NULL,
            docs_completed  INTEGER DEFAULT 0,
            started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at    TIMESTAMPTZ,
            swapped_at      TIMESTAMPTZ,
            initiated_by    TEXT NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS chunk_audit (
            audit_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            doc_id          UUID REFERENCES documents(doc_id),
            chunk_id        TEXT NOT NULL,
            index_name      TEXT NOT NULL,
            embedded_model  TEXT NOT NULL,
            written_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_chunk_audit_doc_id ON chunk_audit(doc_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chunk_audit")
    op.execute("DROP TABLE IF EXISTS query_history")
    op.execute("DROP TABLE IF EXISTS indexing_jobs")
    op.execute("DROP TABLE IF EXISTS documents")
