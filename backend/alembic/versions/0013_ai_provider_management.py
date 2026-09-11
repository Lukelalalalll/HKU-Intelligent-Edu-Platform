"""Platform AI providers and business mappings."""
from alembic import op
import sqlalchemy as sa
from uuid import uuid4

revision = "0013_ai_provider_management"
down_revision = "0012_assignment_attachments"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "ai_providers" not in tables:
        op.create_table("ai_providers",
            sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(120), nullable=False),
            sa.Column("provider_type", sa.String(40), nullable=False, server_default="openai"), sa.Column("base_url", sa.String(500), nullable=False),
            sa.Column("api_key_encrypted", sa.Text(), nullable=False, server_default=""), sa.Column("default_model", sa.String(160), nullable=False),
            sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="120"), sa.Column("capabilities_json", sa.JSON(), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("name"))
        op.create_index("ix_ai_providers_name", "ai_providers", ["name"], unique=True)
        op.create_index("ix_ai_providers_provider_type", "ai_providers", ["provider_type"])
        op.create_index("ix_ai_providers_is_enabled", "ai_providers", ["is_enabled"])
    if "ai_business_bindings" not in tables:
        op.create_table("ai_business_bindings",
            sa.Column("id", sa.String(36), primary_key=True), sa.Column("business_code", sa.String(100), nullable=False), sa.Column("role", sa.String(30), nullable=False), sa.Column("display_name", sa.String(160), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("provider_id", sa.String(36), sa.ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True), sa.Column("model", sa.String(160), nullable=False), sa.Column("embedding_model", sa.String(160), nullable=False), sa.Column("timeout_seconds", sa.Integer(), nullable=True), sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("business_code"))
        op.create_index("ix_ai_business_bindings_business_code", "ai_business_bindings", ["business_code"])
        op.create_index("ix_ai_business_bindings_provider_id", "ai_business_bindings", ["provider_id"])
        op.create_index("ix_ai_business_bindings_is_enabled", "ai_business_bindings", ["is_enabled"])

    # Seed from the latest configured teacher provider, or the environment defaults.
    from app.core.config import settings
    from app.services.ai_gateway import encrypt_api_key
    row = bind.execute(sa.text("SELECT base_url, api_key_encrypted, model, embedding_model, timeout_seconds FROM ppt_provider_configs WHERE api_key_encrypted <> '' ORDER BY updated_at DESC LIMIT 1" )).mappings().first() if "ppt_provider_configs" in tables else None
    base_url = row["base_url"] if row else settings.llm_base_url
    encrypted_key = row["api_key_encrypted"] if row else (encrypt_api_key(settings.llm_api_key) if settings.llm_api_key else "")
    model = row["model"] if row else settings.llm_model
    embedding = row["embedding_model"] if row else settings.embedding_model
    timeout = row["timeout_seconds"] if row else 120
    provider_id = str(uuid4())
    existing = bind.execute(sa.text("SELECT id FROM ai_providers WHERE name='default'" )).first()
    if existing: provider_id = existing[0]
    else:
        provider_type = "deepseek" if "deepseek" in base_url.lower() else "openai"
        bind.execute(sa.text("INSERT INTO ai_providers (id,name,provider_type,base_url,api_key_encrypted,default_model,timeout_seconds,capabilities_json,is_enabled,created_at,updated_at) VALUES (:id,'default',:type,:url,:key,:model,:timeout,:caps,:enabled,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"), {"id": provider_id, "type": provider_type, "url": base_url.rstrip("/"), "key": encrypted_key, "model": model, "timeout": timeout, "caps": '{"json": true, "stream": true}', "enabled": True})
    businesses = [("teacher_ppt_agent", "teacher", "教师 PPT Agent", "PPT 对话、需求分析、课件生成与编辑"), ("teacher_lesson_plan_agent", "teacher", "教师学案 Agent", "学案对话与学案生成"), ("student_lecturer", "student", "学生 AI 讲师", "基于课程材料的 AI 讲师问答")]
    for code, role, name, description in businesses:
        if not bind.execute(sa.text("SELECT 1 FROM ai_business_bindings WHERE business_code=:code"), {"code": code}).first():
            bind.execute(sa.text("INSERT INTO ai_business_bindings (id,business_code,role,display_name,description,provider_id,model,embedding_model,timeout_seconds,is_enabled,created_at,updated_at) VALUES (:id,:code,:role,:name,:description,:provider,:model,:embedding,:timeout,:enabled,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"), {"id": str(uuid4()), "code": code, "role": role, "name": name, "description": description, "provider": provider_id, "model": model, "embedding": embedding, "timeout": timeout, "enabled": True})


def downgrade():
    op.drop_table("ai_business_bindings")
    op.drop_table("ai_providers")



