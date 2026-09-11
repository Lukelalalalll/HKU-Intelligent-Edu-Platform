"""Add assignment attachments."""
from alembic import op
import sqlalchemy as sa

revision = "0012_assignment_attachments"
down_revision = "0011_courseware_rag"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("assignment_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assignment_id", sa.String(36), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_asset_id", sa.String(36), sa.ForeignKey("file_assets.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_assignment_attachments_assignment_id", "assignment_attachments", ["assignment_id"])
    op.create_index("ix_assignment_attachments_file_asset_id", "assignment_attachments", ["file_asset_id"])

def downgrade():
    op.drop_table("assignment_attachments")
