"""Add resumable asynchronous PPT generation state."""
from alembic import op
import sqlalchemy as sa

revision = "0006_ppt_generation_jobs"
down_revision = "0005_zoom_live_class"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    page_cols = {c["name"] for c in inspector.get_columns("ppt_pages")}
    for name, typ, default in (
        ("page_role", sa.String(length=30), "concept"),
        ("content_plan_json", sa.JSON(), "{}"),
        ("visual_plan_json", sa.JSON(), "{}"),
    ):
        if name not in page_cols:
            op.add_column("ppt_pages", sa.Column(name, typ, nullable=False, server_default=default))
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "ppt_generation_jobs" not in tables:
        op.create_table(
            "ppt_generation_jobs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="queued", index=True),
            sa.Column("stage", sa.String(40), nullable=False, server_default="queued"),
            sa.Column("total_pages", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_pages", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_pages", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("current_page_id", sa.String(36), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("planner_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade():
    op.drop_table("ppt_generation_jobs")
    for name in ("visual_plan_json", "content_plan_json", "page_role"):
        op.drop_column("ppt_pages", name)
