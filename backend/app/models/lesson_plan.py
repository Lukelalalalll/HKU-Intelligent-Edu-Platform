from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class LessonPlanProject(Base):
    __tablename__ = "lesson_plan_projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="未命名学案")
    request_text: Mapped[str] = mapped_column(Text, default="")
    current_stage: Mapped[str] = mapped_column(String(40), default="init")
    status: Mapped[str] = mapped_column(String(30), default="active")
    page_size: Mapped[str] = mapped_column(String(20), default="A4")
    orientation: Mapped[str] = mapped_column(String(20), default="portrait")
    template_id: Mapped[str] = mapped_column(String(80), default="hku-green")
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    pages: Mapped[list["LessonPlanPage"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    assets: Mapped[list["LessonPlanAsset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    events: Mapped[list["LessonPlanEvent"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    exports: Mapped[list["LessonPlanExportJob"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class LessonPlanPage(Base):
    __tablename__ = "lesson_plan_pages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("lesson_plan_projects.id", ondelete="CASCADE"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(240), default="")
    page_role: Mapped[str] = mapped_column(String(40), default="content")
    document_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="empty")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    project: Mapped[LessonPlanProject] = relationship(back_populates="pages")


class LessonPlanAsset(Base):
    __tablename__ = "lesson_plan_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("lesson_plan_projects.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(30), default="upload")
    title: Mapped[str] = mapped_column(String(300), default="")
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    project: Mapped[LessonPlanProject] = relationship(back_populates="assets")


class LessonPlanEvent(Base):
    __tablename__ = "lesson_plan_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("lesson_plan_projects.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    project: Mapped[LessonPlanProject] = relationship(back_populates="events")


class LessonPlanExportJob(Base):
    __tablename__ = "lesson_plan_export_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("lesson_plan_projects.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    project: Mapped[LessonPlanProject] = relationship(back_populates="exports")
