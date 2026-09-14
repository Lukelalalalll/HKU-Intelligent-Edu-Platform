from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.entities import utcnow


class FileProcessingDocument(Base):
    __tablename__ = "file_processing_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    file_asset_id: Mapped[str | None] = mapped_column(ForeignKey("file_assets.id", ondelete="SET NULL"), unique=True, index=True, nullable=True)
    filename: Mapped[str] = mapped_column(String(500))
    extension: Mapped[str] = mapped_column(String(30), default="")
    mime_type: Mapped[str] = mapped_column(String(160), default="application/octet-stream")
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    parser: Mapped[str] = mapped_column(String(80), default="pending")
    parser_version: Mapped[str] = mapped_column(String(40), default="1")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artifact_dir: Mapped[str] = mapped_column(String(500), default="")
    manifest_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    jobs: Mapped[list["FileProcessingJob"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    pages: Mapped[list["FileProcessingPage"]] = relationship(back_populates="document", cascade="all, delete-orphan", order_by="FileProcessingPage.page_number")
    chunks: Mapped[list["FileProcessingChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    bindings: Mapped[list["FileContextBinding"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class FileProcessingJob(Base):
    __tablename__ = "file_processing_jobs"
    __table_args__ = (Index("ix_file_processing_jobs_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("file_processing_documents.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(80), default="queued")
    progress: Mapped[float] = mapped_column(Float, default=0)
    processed_pages: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    document: Mapped[FileProcessingDocument] = relationship(back_populates="jobs")


class FileProcessingPage(Base):
    __tablename__ = "file_processing_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number", name="uq_file_processing_page"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("file_processing_documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    width: Mapped[float] = mapped_column(default=0)
    height: Mapped[float] = mapped_column(default=0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    document: Mapped[FileProcessingDocument] = relationship(back_populates="pages")


class FileProcessingChunk(Base):
    __tablename__ = "file_processing_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("file_processing_documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    section: Mapped[str | None] = mapped_column(String(512), nullable=True)
    chunk_type: Mapped[str] = mapped_column(String(40), default="text", index=True)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding_json: Mapped[list | None] = mapped_column(JSON, nullable=True)

    document: Mapped[FileProcessingDocument] = relationship(back_populates="chunks")


class FileContextBinding(Base):
    __tablename__ = "file_context_bindings"
    __table_args__ = (UniqueConstraint("document_id", "target_type", "target_id", name="uq_file_context_binding"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("file_processing_documents.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(40), index=True)
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    visibility: Mapped[str] = mapped_column(String(40), default="owner")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[FileProcessingDocument] = relationship(back_populates="bindings")


class AgentMessageAttachment(Base):
    __tablename__ = "agent_message_attachments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    message_id: Mapped[str] = mapped_column(ForeignKey("agent_messages.id", ondelete="CASCADE"), index=True)
    file_asset_id: Mapped[str] = mapped_column(ForeignKey("file_assets.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("file_processing_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SubmissionAttachment(Base):
    __tablename__ = "submission_attachments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    file_asset_id: Mapped[str] = mapped_column(ForeignKey("file_assets.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("file_processing_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
