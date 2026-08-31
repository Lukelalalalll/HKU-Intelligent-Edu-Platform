"""PPT theme selection and layout assignment state."""
from alembic import op
import sqlalchemy as sa

revision = "0004_ppt_theme_flow"
down_revision = "0003_course_semesters"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    cols = {c["name"] for c in inspector.get_columns("ppt_projects")}
    additions = [
        ("theme_id", sa.String(length=120), None),
        ("theme_config", sa.JSON(), "{}"),
        ("layout_assignments", sa.JSON(), "{}"),
        ("design_status", sa.String(length=30), "pending"),
    ]
    for name, typ, default in additions:
        if name not in cols:
            kwargs = {"nullable": False, "server_default": default} if default is not None else {"nullable": True}
            op.add_column("ppt_projects", sa.Column(name, typ, **kwargs))


def downgrade():
    inspector = sa.inspect(op.get_bind())
    cols = {c["name"] for c in inspector.get_columns("ppt_projects")}
    for name in ("design_status", "layout_assignments", "theme_config", "theme_id"):
        if name in cols:
            op.drop_column("ppt_projects", name)
