"""Track durable queue task identifiers and attempts."""

from alembic import op
import sqlalchemy as sa

revision = "0015_background_job_metadata"
down_revision = "0014_file_processing"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("ppt_generation_jobs", "ppt_export_jobs"):
        op.add_column(table, sa.Column("queue_task_id", sa.String(255), nullable=True))
        op.create_index(f"ix_{table}_queue_task_id", table, ["queue_task_id"])
        op.add_column(table, sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ppt_export_jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("ppt_export_jobs", "started_at")
    for table in ("ppt_export_jobs", "ppt_generation_jobs"):
        op.drop_column(table, "attempts")
        op.drop_index(f"ix_{table}_queue_task_id", table_name=table)
        op.drop_column(table, "queue_task_id")
