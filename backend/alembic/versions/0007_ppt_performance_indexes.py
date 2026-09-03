"""Add indexes supporting bounded history and event-stream queries."""
from alembic import op

revision = "0007_ppt_performance_indexes"
down_revision = "0006_ppt_generation_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_ppt_messages_project_page_created", "ppt_messages", ["project_id", "page_id", "created_at"])
    op.create_index("ix_ppt_agent_events_project_id_id", "ppt_agent_events", ["project_id", "id"])
    op.create_index("ix_ppt_source_collections_project_page", "ppt_source_collections", ["project_id", "page_id"])


def downgrade():
    op.drop_index("ix_ppt_source_collections_project_page", table_name="ppt_source_collections")
    op.drop_index("ix_ppt_agent_events_project_id_id", table_name="ppt_agent_events")
    op.drop_index("ix_ppt_messages_project_page_created", table_name="ppt_messages")
