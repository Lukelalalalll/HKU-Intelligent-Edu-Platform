"""Add persistent lecture and tutorial course materials."""
from alembic import op
import sqlalchemy as sa


revision = "0008_course_materials"
down_revision = "0007_ppt_performance_indexes"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    if "course_chapters" not in existing:
        op.create_table(
            "course_chapters",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("course_id", sa.String(length=36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("kind", sa.String(length=20), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("kind IN ('lecture', 'tutorial')", name="ck_course_chapter_kind"),
            sa.UniqueConstraint("course_id", "kind", "title", name="uq_course_chapter_title"),
        )
        op.create_index("ix_course_chapters_course_id", "course_chapters", ["course_id"])
        op.create_index("ix_course_chapters_kind", "course_chapters", ["kind"])
    if "course_materials" not in existing:
        op.create_table(
            "course_materials",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("chapter_id", sa.String(length=36), sa.ForeignKey("course_chapters.id", ondelete="CASCADE"), nullable=False),
            sa.Column("file_asset_id", sa.String(length=36), sa.ForeignKey("file_assets.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("uploaded_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("file_asset_id", name="uq_course_material_file_asset"),
        )
        op.create_index("ix_course_materials_chapter_id", "course_materials", ["chapter_id"])
        op.create_index("ix_course_materials_file_asset_id", "course_materials", ["file_asset_id"])
        op.create_index("ix_course_materials_uploaded_by", "course_materials", ["uploaded_by"])


def downgrade():
    op.drop_index("ix_course_materials_uploaded_by", table_name="course_materials")
    op.drop_index("ix_course_materials_file_asset_id", table_name="course_materials")
    op.drop_index("ix_course_materials_chapter_id", table_name="course_materials")
    op.drop_table("course_materials")
    op.drop_index("ix_course_chapters_kind", table_name="course_chapters")
    op.drop_index("ix_course_chapters_course_id", table_name="course_chapters")
    op.drop_table("course_chapters")
