"""Zoom live classroom integration."""
from alembic import op
import sqlalchemy as sa

revision = "0005_zoom_live_class"
down_revision = "0004_ppt_theme_flow"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    course_cols = {c["name"] for c in inspector.get_columns("courses")}
    if "timezone" not in course_cols:
        op.add_column("courses", sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Hong_Kong"))
    schedule_cols = {c["name"] for c in inspector.get_columns("course_schedules")}
    if "timezone" not in schedule_cols:
        op.add_column("course_schedules", sa.Column("timezone", sa.String(length=64), nullable=True))

    if not inspector.has_table("course_zoom_meetings"):
        op.create_table(
            "course_zoom_meetings",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("course_id", sa.String(length=36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("schedule_id", sa.String(length=36), sa.ForeignKey("course_schedules.id", ondelete="CASCADE"), nullable=False),
            sa.Column("zoom_meeting_id", sa.String(length=120), nullable=False),
            sa.Column("topic", sa.String(length=200), nullable=False),
            sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Hong_Kong"),
            sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("join_url", sa.String(length=1000), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("course_id", "schedule_id", name="uq_course_zoom_meeting_schedule"),
            sa.UniqueConstraint("zoom_meeting_id", name="uq_course_zoom_meetings_zoom_id"),
        )
        op.create_index("ix_course_zoom_meetings_course_id", "course_zoom_meetings", ["course_id"])
        op.create_index("ix_course_zoom_meetings_schedule_id", "course_zoom_meetings", ["schedule_id"])
        op.create_index("ix_course_zoom_meetings_zoom_meeting_id", "course_zoom_meetings", ["zoom_meeting_id"])
        op.create_index("ix_course_zoom_meetings_status", "course_zoom_meetings", ["status"])

    recording_cols = {c["name"] for c in inspector.get_columns("recording_sessions")}
    additions = [
        ("zoom_meeting_fk", sa.String(length=36), True),
        ("schedule_id", sa.String(length=36), True),
        ("occurrence_start", sa.DateTime(timezone=True), True),
        ("occurrence_end", sa.DateTime(timezone=True), True),
        ("last_webhook_event_id", sa.String(length=160), True),
    ]
    for name, typ, nullable in additions:
        if name not in recording_cols:
            op.add_column("recording_sessions", sa.Column(name, typ, nullable=nullable))
    if "ix_recording_sessions_zoom_meeting_fk" not in {i["name"] for i in inspector.get_indexes("recording_sessions")}: 
        op.create_index("ix_recording_sessions_zoom_meeting_fk", "recording_sessions", ["zoom_meeting_fk"])
    if "ix_recording_sessions_schedule_id" not in {i["name"] for i in inspector.get_indexes("recording_sessions")}: 
        op.create_index("ix_recording_sessions_schedule_id", "recording_sessions", ["schedule_id"])


def downgrade():
    op.drop_index("ix_recording_sessions_schedule_id", table_name="recording_sessions")
    op.drop_index("ix_recording_sessions_zoom_meeting_fk", table_name="recording_sessions")
    for name in ("last_webhook_event_id", "occurrence_end", "occurrence_start", "schedule_id", "zoom_meeting_fk"):
        op.drop_column("recording_sessions", name)
    op.drop_index("ix_course_zoom_meetings_status", table_name="course_zoom_meetings")
    op.drop_index("ix_course_zoom_meetings_zoom_meeting_id", table_name="course_zoom_meetings")
    op.drop_index("ix_course_zoom_meetings_schedule_id", table_name="course_zoom_meetings")
    op.drop_index("ix_course_zoom_meetings_course_id", table_name="course_zoom_meetings")
    op.drop_table("course_zoom_meetings")
    op.drop_column("course_schedules", "timezone")
    op.drop_column("courses", "timezone")
