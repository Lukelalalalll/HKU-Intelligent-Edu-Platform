from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VideoProject(Base):
    __tablename__ = "video_projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="未命名教学视频")
    description: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(20), default="coze")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    language: Mapped[str] = mapped_column(String(30), default="zh-HK")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=120)
    style: Mapped[str] = mapped_column(String(60), default="lecture")
    input_text: Mapped[str] = mapped_column(Text, default="")
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sources: Mapped[list["VideoSource"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    scenes: Mapped[list["VideoScene"]] = relationship(back_populates="project", cascade="all, delete-orphan", order_by="VideoScene.order_index")
    jobs: Mapped[list["VideoGenerationJob"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    assets: Mapped[list["VideoAsset"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class VideoSource(Base):
    __tablename__ = "video_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id", ondelete="CASCADE"), index=True)
    file_asset_id: Mapped[str | None] = mapped_column(ForeignKey("file_assets.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(30), default="text")
    title: Mapped[str] = mapped_column(String(255), default="讲稿")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    project: Mapped[VideoProject] = relationship(back_populates="sources")


class VideoScene(Base):
    __tablename__ = "video_scenes"
    __table_args__ = (UniqueConstraint("project_id", "order_index", name="uq_video_scene_order"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(200), default="场景")
    narration: Mapped[str] = mapped_column(Text, default="")
    onscreen_text: Mapped[str] = mapped_column(Text, default="")
    visual_prompt: Mapped[str] = mapped_column(Text, default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=15)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    project: Mapped[VideoProject] = relationship(back_populates="scenes")


class VideoGenerationJob(Base):
    __tablename__ = "video_generation_jobs"
    __table_args__ = (UniqueConstraint("owner_id", "idempotency_key", name="uq_video_job_owner_idempotency"), Index("ix_video_jobs_project_created", "project_id", "created_at"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id", ondelete="CASCADE"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), default="coze")
    provider_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(80), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_scene: Mapped[int] = mapped_column(Integer, default=0)
    total_scenes: Mapped[int] = mapped_column(Integer, default=0)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    queue_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    project: Mapped[VideoProject] = relationship(back_populates="jobs")


class VideoAsset(Base):
    __tablename__ = "video_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("video_generation_jobs.id", ondelete="CASCADE"), index=True)
    asset_type: Mapped[str] = mapped_column(String(30), default="video")
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    public_url: Mapped[str | None] = mapped_column(String(800), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    project: Mapped[VideoProject] = relationship(back_populates="assets")
