"""Lesson plan agent tables.

The lesson-plan models shipped before this revision and some development
databases already contain the tables (``app.seed`` created them through
``Base.metadata.create_all``).  This revision is therefore an *adoption*
migration: it creates only the tables that are missing, so a fresh database
matches the models while existing databases keep their rows.  The downgrade is
intentionally a no-op for the same reason.
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_lesson_plan_agent"
down_revision = "0020_file_processing_active_job"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade():
    existing = _tables()

    if "lesson_plan_projects" not in existing:
        op.create_table(
            "lesson_plan_projects",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("request_text", sa.Text(), nullable=False),
            sa.Column("current_stage", sa.String(40), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("page_size", sa.String(20), nullable=False),
            sa.Column("orientation", sa.String(20), nullable=False),
            sa.Column("template_id", sa.String(80), nullable=False),
            sa.Column("settings_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_lesson_plan_projects_owner_id", "lesson_plan_projects", ["owner_id"])
        op.create_index("ix_lesson_plan_projects_course_id", "lesson_plan_projects", ["course_id"])

    if "lesson_plan_pages" not in existing:
        op.create_table(
            "lesson_plan_pages",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("lesson_plan_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(240), nullable=False),
            sa.Column("page_role", sa.String(40), nullable=False),
            sa.Column("document_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
        )
        op.create_index("ix_lesson_plan_pages_project_id", "lesson_plan_pages", ["project_id"])

    if "lesson_plan_assets" not in existing:
        op.create_table(
            "lesson_plan_assets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("lesson_plan_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_type", sa.String(30), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("file_path", sa.Text(), nullable=True),
            sa.Column("public_url", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
        )
        op.create_index("ix_lesson_plan_assets_project_id", "lesson_plan_assets", ["project_id"])

    if "lesson_plan_events" not in existing:
        op.create_table(
            "lesson_plan_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("lesson_plan_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("event_type", sa.String(80), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_lesson_plan_events_project_id", "lesson_plan_events", ["project_id"])
        op.create_index("ix_lesson_plan_events_event_type", "lesson_plan_events", ["event_type"])

    if "lesson_plan_export_jobs" not in existing:
        op.create_table(
            "lesson_plan_export_jobs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("lesson_plan_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("pdf_path", sa.Text(), nullable=True),
            sa.Column("html_path", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_lesson_plan_export_jobs_project_id", "lesson_plan_export_jobs", ["project_id"])

    if "lesson_plan_messages" not in existing:
        op.create_table(
            "lesson_plan_messages",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("lesson_plan_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("content_md", sa.Text(), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_lesson_plan_messages_project_id", "lesson_plan_messages", ["project_id"])
        op.create_index("ix_lesson_plan_messages_created_at", "lesson_plan_messages", ["created_at"])


def downgrade():
    # Adoption migration: the tables may pre-date this revision, so dropping
    # them would destroy data that was never created here.
    pass
