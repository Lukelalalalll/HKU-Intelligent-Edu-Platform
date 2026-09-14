"""Durable task outbox for broker hand-off."""

from alembic import op
import sqlalchemy as sa

revision = "0016_task_outbox"
down_revision = "0015_background_job_metadata"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "task_outbox",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("task_type", sa.String(80), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_task_outbox_status", "task_outbox", ["status"])
    op.create_index("ix_task_outbox_status_created", "task_outbox", ["status", "created_at"])


def downgrade():
    op.drop_table("task_outbox")
