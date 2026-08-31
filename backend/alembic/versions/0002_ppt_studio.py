"""PPT studio project state, messages, checkpoints and document versions."""
from alembic import op
import sqlalchemy as sa

revision = "0002_ppt_studio"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _columns(table):
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ppt_projects" in inspector.get_table_names():
        cols = _columns("ppt_projects")
        if "status" not in cols:
            op.add_column("ppt_projects", sa.Column("status", sa.String(length=30), nullable=False, server_default="active"))
        if "active_page_id" not in cols:
            op.add_column("ppt_projects", sa.Column("active_page_id", sa.String(length=36), nullable=True))
        if "latest_checkpoint_code" not in cols:
            op.add_column("ppt_projects", sa.Column("latest_checkpoint_code", sa.String(length=80), nullable=True))
    if "ppt_pages" in inspector.get_table_names():
        cols = _columns("ppt_pages")
        if "document_revision" not in cols:
            op.add_column("ppt_pages", sa.Column("document_revision", sa.Integer(), nullable=False, server_default="1"))
        if "current_document_version_id" not in cols:
            op.add_column("ppt_pages", sa.Column("current_document_version_id", sa.String(length=36), nullable=True))

    existing = set(inspector.get_table_names())
    if "ppt_messages" not in existing:
        op.create_table(
            "ppt_messages",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), sa.ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("page_id", sa.String(length=36), sa.ForeignKey("ppt_pages.id", ondelete="SET NULL"), nullable=True),
            sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
            sa.Column("stage", sa.String(length=30), nullable=False, server_default="init"),
            sa.Column("scope_type", sa.String(length=20), nullable=False, server_default="project"),
            sa.Column("content_md", sa.Text(), nullable=False, server_default=""),
            sa.Column("structured_payload_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_ppt_messages_project_id", "ppt_messages", ["project_id"])
        op.create_index("ix_ppt_messages_page_id", "ppt_messages", ["page_id"])
    if "ppt_checkpoints" not in existing:
        op.create_table(
            "ppt_checkpoints",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), sa.ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("checkpoint_code", sa.String(length=80), nullable=False),
            sa.Column("stage", sa.String(length=30), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("summary_md", sa.Text(), nullable=False, server_default=""),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_ppt_checkpoints_project_id", "ppt_checkpoints", ["project_id"])
    if "ppt_document_versions" not in existing:
        op.create_table(
            "ppt_document_versions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), sa.ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("page_id", sa.String(length=36), sa.ForeignKey("ppt_pages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("document_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_ppt_document_versions_project_id", "ppt_document_versions", ["project_id"])
        op.create_index("ix_ppt_document_versions_page_id", "ppt_document_versions", ["page_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in ("ppt_document_versions", "ppt_checkpoints", "ppt_messages"):
        if table in inspector.get_table_names():
            op.drop_table(table)
    if "ppt_pages" in inspector.get_table_names():
        cols = _columns("ppt_pages")
        if "current_document_version_id" in cols:
            op.drop_column("ppt_pages", "current_document_version_id")
        if "document_revision" in cols:
            op.drop_column("ppt_pages", "document_revision")
    if "ppt_projects" in inspector.get_table_names():
        cols = _columns("ppt_projects")
        for col in ("latest_checkpoint_code", "active_page_id", "status"):
            if col in cols:
                op.drop_column("ppt_projects", col)
