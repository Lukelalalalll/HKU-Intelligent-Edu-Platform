"""Unified file processing documents, jobs, structured pages/chunks and bindings."""
from alembic import op
import sqlalchemy as sa

revision = "0014_file_processing"
down_revision = "0013_ai_provider_management"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("file_processing_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("file_asset_id", sa.String(36), sa.ForeignKey("file_assets.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("filename", sa.String(500), nullable=False), sa.Column("extension", sa.String(30), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(160), nullable=False, server_default="application/octet-stream"), sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"), sa.Column("parser", sa.String(80), nullable=False, server_default="pending"),
        sa.Column("parser_version", sa.String(40), nullable=False, server_default="1"), sa.Column("page_count", sa.Integer()), sa.Column("artifact_dir", sa.String(500), nullable=False, server_default=""),
        sa.Column("manifest_json", sa.JSON(), nullable=False, server_default="{}"), sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_file_processing_documents_file_asset_id", "file_processing_documents", ["file_asset_id"])
    op.create_index("ix_file_processing_documents_sha256", "file_processing_documents", ["sha256"])
    op.create_index("ix_file_processing_documents_status", "file_processing_documents", ["status"])
    op.create_table("file_processing_jobs",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_id", sa.String(36), sa.ForeignKey("file_processing_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"), sa.Column("stage", sa.String(80), nullable=False, server_default="queued"), sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("processed_pages", sa.Integer(), nullable=False, server_default="0"), sa.Column("total_pages", sa.Integer()), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"), sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text()), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_file_processing_jobs_document_id", "file_processing_jobs", ["document_id"]); op.create_index("ix_file_processing_jobs_status", "file_processing_jobs", ["status"]); op.create_index("ix_file_processing_jobs_status_created", "file_processing_jobs", ["status", "created_at"])
    op.create_table("file_processing_pages", sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_id", sa.String(36), sa.ForeignKey("file_processing_documents.id", ondelete="CASCADE"), nullable=False), sa.Column("page_number", sa.Integer(), nullable=False), sa.Column("width", sa.Float(), nullable=False, server_default="0"), sa.Column("height", sa.Float(), nullable=False, server_default="0"), sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"), sa.UniqueConstraint("document_id", "page_number", name="uq_file_processing_page"))
    op.create_index("ix_file_processing_pages_document_id", "file_processing_pages", ["document_id"])
    op.create_table("file_processing_chunks", sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_id", sa.String(36), sa.ForeignKey("file_processing_documents.id", ondelete="CASCADE"), nullable=False), sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"), sa.Column("page_number", sa.Integer()), sa.Column("section", sa.String(512)), sa.Column("chunk_type", sa.String(40), nullable=False, server_default="text"), sa.Column("content", sa.Text(), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"), sa.Column("embedding_json", sa.JSON()))
    for name, column in (("document_id", "document_id"), ("page_number", "page_number"), ("chunk_type", "chunk_type")): op.create_index(f"ix_file_processing_chunks_{name}", "file_processing_chunks", [column])
    op.create_table("file_context_bindings", sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_id", sa.String(36), sa.ForeignKey("file_processing_documents.id", ondelete="CASCADE"), nullable=False), sa.Column("target_type", sa.String(40), nullable=False), sa.Column("target_id", sa.String(36), nullable=False), sa.Column("visibility", sa.String(40), nullable=False, server_default="owner"), sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id", ondelete="CASCADE")), sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("document_id", "target_type", "target_id", name="uq_file_context_binding"))
    for name, column in (("document_id", "document_id"), ("target_type", "target_type"), ("target_id", "target_id"), ("owner_id", "owner_id"), ("course_id", "course_id")): op.create_index(f"ix_file_context_bindings_{name}", "file_context_bindings", [column])
    op.create_table("agent_message_attachments", sa.Column("id", sa.String(36), primary_key=True), sa.Column("message_id", sa.String(36), sa.ForeignKey("agent_messages.id", ondelete="CASCADE"), nullable=False), sa.Column("file_asset_id", sa.String(36), sa.ForeignKey("file_assets.id", ondelete="CASCADE"), nullable=False), sa.Column("document_id", sa.String(36), sa.ForeignKey("file_processing_documents.id", ondelete="SET NULL")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for name, column in (("message_id", "message_id"), ("file_asset_id", "file_asset_id"), ("document_id", "document_id")): op.create_index(f"ix_agent_message_attachments_{name}", "agent_message_attachments", [column])
    op.create_table("submission_attachments", sa.Column("id", sa.String(36), primary_key=True), sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False), sa.Column("file_asset_id", sa.String(36), sa.ForeignKey("file_assets.id", ondelete="CASCADE"), nullable=False), sa.Column("document_id", sa.String(36), sa.ForeignKey("file_processing_documents.id", ondelete="SET NULL")), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for name, column in (("submission_id", "submission_id"), ("file_asset_id", "file_asset_id"), ("document_id", "document_id")): op.create_index(f"ix_submission_attachments_{name}", "submission_attachments", [column])


def downgrade():
    for table in ("submission_attachments", "agent_message_attachments", "file_context_bindings", "file_processing_chunks", "file_processing_pages", "file_processing_jobs", "file_processing_documents"): op.drop_table(table)
