from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AiProvider(Base):
    __tablename__ = "ai_providers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    provider_type: Mapped[str] = mapped_column(String(40), default="openai", index=True)
    base_url: Mapped[str] = mapped_column(String(500), default="https://api.openai.com/v1")
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    default_model: Mapped[str] = mapped_column(String(160), default="gpt-4o-mini")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120)
    capabilities_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    bindings: Mapped[list["AiBusinessBinding"]] = relationship(back_populates="provider")


class AiBusinessBinding(Base):
    __tablename__ = "ai_business_bindings"
    __table_args__ = (UniqueConstraint("business_code", name="uq_ai_business_binding_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    business_code: Mapped[str] = mapped_column(String(100), index=True)
    role: Mapped[str] = mapped_column(String(30), default="admin")
    display_name: Mapped[str] = mapped_column(String(160), default="AI 业务")
    description: Mapped[str] = mapped_column(Text, default="")
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True, index=True)
    model: Mapped[str] = mapped_column(String(160), default="")
    embedding_model: Mapped[str] = mapped_column(String(160), default="")
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    provider: Mapped[AiProvider | None] = relationship(back_populates="bindings")
