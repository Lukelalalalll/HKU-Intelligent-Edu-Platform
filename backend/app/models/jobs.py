from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.entities import utcnow


class TaskOutbox(Base):
    """Durable hand-off between a committed DB transaction and the broker."""

    __tablename__ = "task_outbox"
    __table_args__ = (
        Index("ix_task_outbox_status_created", "status", "created_at"),
        Index("ix_task_outbox_retry", "status", "next_run_at"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
