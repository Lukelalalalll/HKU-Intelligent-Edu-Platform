"""Prevent duplicate active processing jobs per document."""
from alembic import op
import sqlalchemy as sa

revision = "0020_file_processing_active_job"
down_revision = "0019_task_outbox_leases"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "uq_file_processing_active_document",
        "file_processing_jobs",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
        sqlite_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade():
    op.drop_index("uq_file_processing_active_document", table_name="file_processing_jobs")
