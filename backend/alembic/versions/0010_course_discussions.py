"""Add course-scoped discussion comments and likes."""

from alembic import op
import sqlalchemy as sa


revision = "0010_course_discussions"
down_revision = "0009_course_code_cleanup"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "discussion_comments" not in existing:
        op.create_table(
            "discussion_comments",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("course_id", sa.String(length=36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("author_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("parent_id", sa.String(length=36), sa.ForeignKey("discussion_comments.id", ondelete="CASCADE"), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_discussion_comments_course_id", "discussion_comments", ["course_id"])
        op.create_index("ix_discussion_comments_author_id", "discussion_comments", ["author_id"])
        op.create_index("ix_discussion_comments_parent_id", "discussion_comments", ["parent_id"])
        op.create_index("ix_discussion_comments_course_activity", "discussion_comments", ["course_id", "updated_at"])
    if "discussion_likes" not in existing:
        op.create_table(
            "discussion_likes",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("comment_id", sa.String(length=36), sa.ForeignKey("discussion_comments.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("comment_id", "user_id", name="uq_discussion_like_comment_user"),
        )
        op.create_index("ix_discussion_likes_comment_id", "discussion_likes", ["comment_id"])
        op.create_index("ix_discussion_likes_user_id", "discussion_likes", ["user_id"])


def downgrade():
    op.drop_index("ix_discussion_likes_user_id", table_name="discussion_likes")
    op.drop_index("ix_discussion_likes_comment_id", table_name="discussion_likes")
    op.drop_table("discussion_likes")
    op.drop_index("ix_discussion_comments_course_activity", table_name="discussion_comments")
    op.drop_index("ix_discussion_comments_parent_id", table_name="discussion_comments")
    op.drop_index("ix_discussion_comments_author_id", table_name="discussion_comments")
    op.drop_index("ix_discussion_comments_course_id", table_name="discussion_comments")
    op.drop_table("discussion_comments")
