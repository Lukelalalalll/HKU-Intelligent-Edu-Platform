"""Add academic year and semester metadata to courses."""

from alembic import op
import sqlalchemy as sa


revision = "0003_course_semesters"
down_revision = "0002_ppt_studio"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "courses" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("courses")}
    if "academic_year_start" not in columns:
        op.add_column("courses", sa.Column("academic_year_start", sa.Integer(), nullable=True))
    if "semester" not in columns:
        op.add_column("courses", sa.Column("semester", sa.String(length=32), nullable=True))

    # This is a deliberate data reset: the old course records have no reliable
    # academic-term ownership, so the new seed data becomes the source of truth.
    for table in ("submissions", "assignments", "enrollments", "course_schedules"):
        if table in tables:
            bind.execute(sa.text(f"DELETE FROM {table}"))
    bind.execute(sa.text("DELETE FROM courses"))

    with op.batch_alter_table("courses") as batch:
        batch.alter_column("academic_year_start", existing_type=sa.Integer(), nullable=False, server_default=None)
        batch.alter_column("semester", existing_type=sa.String(length=32), nullable=False, server_default=None)
        existing_checks = {check.get("name") for check in inspector.get_check_constraints("courses")}
        if "ck_courses_semester" not in existing_checks:
            batch.create_check_constraint("ck_courses_semester", "semester IN ('semester_1', 'semester_2', 'summer')")

    existing_indexes = {index["name"] for index in inspector.get_indexes("courses")}
    if "ix_courses_academic_year_start" not in existing_indexes:
        op.create_index("ix_courses_academic_year_start", "courses", ["academic_year_start"])
    if "ix_courses_semester" not in existing_indexes:
        op.create_index("ix_courses_semester", "courses", ["semester"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "courses" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("courses")}
    if "ix_courses_semester" in indexes:
        op.drop_index("ix_courses_semester", table_name="courses")
    if "ix_courses_academic_year_start" in indexes:
        op.drop_index("ix_courses_academic_year_start", table_name="courses")
    with op.batch_alter_table("courses") as batch:
        batch.drop_constraint("ck_courses_semester", type_="check")
        batch.drop_column("semester")
        batch.drop_column("academic_year_start")
