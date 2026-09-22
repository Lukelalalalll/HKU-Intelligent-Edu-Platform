"""Add retry scheduling and leases to the transactional task outbox."""

from alembic import op
import sqlalchemy as sa


revision = "0019_task_outbox_leases"
down_revision = "0018_ai_video"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("task_outbox", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("task_outbox", sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("task_outbox", sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_task_outbox_retry", "task_outbox", ["status", "next_run_at"])


def downgrade():
    op.drop_index("ix_task_outbox_retry", table_name="task_outbox")
    op.drop_column("task_outbox", "lease_until")
    op.drop_column("task_outbox", "next_run_at")
    op.drop_column("task_outbox", "max_attempts")
