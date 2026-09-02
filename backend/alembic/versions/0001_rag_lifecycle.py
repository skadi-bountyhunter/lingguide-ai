"""建立 RAG 版本、manifest 和任务表。"""
from alembic import op
import sqlalchemy as sa

revision = "0001_rag_lifecycle"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("normalized_sha256", sa.String(64), server_default=""),
        sa.Column("chunking_config_hash", sa.String(64), server_default=""),
        sa.Column("state", sa.String(20), server_default="building"),
        sa.Column("supersedes_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("activated_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", "version_no", name="uq_document_versions_document_no"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_state", "document_versions", ["state"])

    op.create_table(
        "index_manifests",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("version", sa.String(64), nullable=False, unique=True),
        sa.Column("state", sa.String(20), server_default="building"),
        sa.Column("vector_collection", sa.String(255), server_default=""),
        sa.Column("fts_namespace", sa.String(255), server_default=""),
        sa.Column("embedding_model", sa.String(255), server_default=""),
        sa.Column("config_hash", sa.String(64), server_default=""),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("vector_count", sa.Integer(), server_default="0"),
        sa.Column("fts_count", sa.Integer(), server_default="0"),
        sa.Column("content_hash", sa.String(64), server_default=""),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("activated_at", sa.DateTime()),
        sa.Column("retired_at", sa.DateTime()),
    )
    op.create_index("ix_index_manifests_state", "index_manifests", ["state"])

    op.create_table(
        "index_jobs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("target_version", sa.String(64)),
        sa.Column("state", sa.String(20), server_default="queued"),
        sa.Column("attempt", sa.Integer(), server_default="0"),
        sa.Column("lease_owner", sa.String(128)),
        sa.Column("lease_expires_at", sa.DateTime()),
        sa.Column("error_message", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_index_jobs_state", "index_jobs", ["state"])


def downgrade() -> None:
    op.drop_table("index_jobs")
    op.drop_table("index_manifests")
    op.drop_table("document_versions")
