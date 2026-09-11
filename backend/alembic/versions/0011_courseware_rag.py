"""Add courseware RAG ingestion and chunks."""
from alembic import op
import sqlalchemy as sa
revision = "0011_courseware_rag"
down_revision = "0010_course_discussions"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("course_material_ingestions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("material_id", sa.String(36), sa.ForeignKey("course_materials.id", ondelete="CASCADE"), unique=True, nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="pending"), sa.Column("parser", sa.String(40), nullable=False, server_default="builtin"), sa.Column("error_message", sa.Text()), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("index_version", sa.String(40), nullable=False, server_default="1"))
    op.create_index("ix_course_material_ingestions_material_id", "course_material_ingestions", ["material_id"])
    op.create_index("ix_course_material_ingestions_status", "course_material_ingestions", ["status"])
    op.create_table("course_material_chunks", sa.Column("id", sa.String(36), primary_key=True), sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False), sa.Column("chapter_id", sa.String(36), sa.ForeignKey("course_chapters.id", ondelete="CASCADE"), nullable=False), sa.Column("material_id", sa.String(36), sa.ForeignKey("course_materials.id", ondelete="CASCADE"), nullable=False), sa.Column("chunk_id", sa.String(120), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("page_number", sa.Integer()), sa.Column("source_anchor", sa.String(255)), sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"))
    for col in ("course_id", "chapter_id", "material_id", "chunk_id"): op.create_index(f"ix_course_material_chunks_{col}", "course_material_chunks", [col])
def downgrade():
    op.drop_table("course_material_chunks"); op.drop_table("course_material_ingestions")
