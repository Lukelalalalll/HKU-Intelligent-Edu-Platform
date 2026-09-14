"""Project-scoped image assets for the PPT editor."""
from alembic import op
import sqlalchemy as sa

revision = "0017_ppt_editor_assets"
down_revision = "0016_task_outbox"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "ppt_editor_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", sa.String(36), sa.ForeignKey("ppt_pages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(500), nullable=False, server_default="image"),
        sa.Column("storage_path", sa.Text(), nullable=False, server_default=""),
        sa.Column("mime", sa.String(120), nullable=False, server_default="image/png"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(64), nullable=False, server_default=""),
        sa.Column("alt", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("license", sa.String(200), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ppt_editor_assets_project_id", "ppt_editor_assets", ["project_id"])
    op.create_index("ix_ppt_editor_assets_page_id", "ppt_editor_assets", ["page_id"])

def downgrade():
    op.drop_table("ppt_editor_assets")
