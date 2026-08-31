from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class PptProject(Base):
    __tablename__ = "ppt_projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="未命名课件")
    request_text: Mapped[str] = mapped_column(Text, default="")
    current_stage: Mapped[str] = mapped_column(String(30), default="init")
    status: Mapped[str] = mapped_column(String(30), default="active")
    active_page_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    latest_checkpoint_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    page_count_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    style_preset: Mapped[str | None] = mapped_column(String(80), nullable=True)
    theme_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    theme_config: Mapped[dict] = mapped_column(JSON, default=dict)
    layout_assignments: Mapped[dict] = mapped_column(JSON, default=dict)
    design_status: Mapped[str] = mapped_column(String(30), default="pending")
    background_asset_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    pages: Mapped[list["PptPage"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    sources: Mapped[list["PptSourceCollection"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    runs: Mapped[list["PptAgentRun"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    events: Mapped[list["PptAgentEvent"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    exports: Mapped[list["PptExportJob"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    messages: Mapped[list["PptMessage"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    checkpoints: Mapped[list["PptCheckpoint"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    document_versions: Mapped[list["PptDocumentVersion"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class PptRequirement(Base):
    __tablename__ = "ppt_requirements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    questions_json: Mapped[list] = mapped_column(JSON, default=list)
    answers_json: Mapped[dict] = mapped_column(JSON, default=dict)
    init_queries_json: Mapped[list] = mapped_column(JSON, default=list)
    page_count_options_json: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class PptOutlineVersion(Base):
    __tablename__ = "ppt_outline_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="ready")
    outline_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class PptPage(Base):
    __tablename__ = "ppt_pages"
    __table_args__ = (UniqueConstraint("project_id", "sort_order", name="uq_ppt_page_order"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), index=True)
    section_title: Mapped[str] = mapped_column(String(200), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(240), default="")
    bullets_json: Mapped[list] = mapped_column(JSON, default=list)
    statuses_json: Mapped[dict] = mapped_column(JSON, default=lambda: {k: "empty" for k in ("outline", "search", "summary", "draft", "design")})
    search_queries_json: Mapped[list] = mapped_column(JSON, default=list)
    summary_md: Mapped[str] = mapped_column(Text, default="")
    citations_json: Mapped[list] = mapped_column(JSON, default=list)
    draft_document_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    design_document_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    speaker_notes: Mapped[str] = mapped_column(Text, default="")
    page_role: Mapped[str] = mapped_column(String(30), default="concept")
    content_plan_json: Mapped[dict] = mapped_column(JSON, default=dict)
    visual_plan_json: Mapped[dict] = mapped_column(JSON, default=dict)
    document_revision: Mapped[int] = mapped_column(Integer, default=1)
    current_document_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    project: Mapped[PptProject] = relationship(back_populates="pages")


class PptMessage(Base):
    __tablename__ = "ppt_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("ppt_pages.id", ondelete="SET NULL"), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    stage: Mapped[str] = mapped_column(String(30), default="init")
    scope_type: Mapped[str] = mapped_column(String(20), default="project")
    content_md: Mapped[str] = mapped_column(Text, default="")
    structured_payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    project: Mapped[PptProject] = relationship(back_populates="messages")


class PptCheckpoint(Base):
    __tablename__ = "ppt_checkpoints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), index=True)
    checkpoint_code: Mapped[str] = mapped_column(String(80))
    stage: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    summary_md: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    project: Mapped[PptProject] = relationship(back_populates="checkpoints")


class PptDocumentVersion(Base):
    __tablename__ = "ppt_document_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("ppt_pages.id", ondelete="CASCADE"), index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="active")
    document_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    project: Mapped[PptProject] = relationship(back_populates="document_versions")


class PptSourceCollection(Base):
    __tablename__ = "ppt_source_collections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("ppt_pages.id", ondelete="CASCADE"), nullable=True, index=True)
    collection_type: Mapped[str] = mapped_column(String(30), default="init_corpus")
    title: Mapped[str] = mapped_column(String(200), default="资料池")
    project: Mapped[PptProject] = relationship(back_populates="sources")
    documents: Mapped[list["PptSourceDocument"]] = relationship(back_populates="collection", cascade="all, delete-orphan")


class PptSourceDocument(Base):
    __tablename__ = "ppt_source_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    collection_id: Mapped[str] = mapped_column(ForeignKey("ppt_source_collections.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(30), default="upload")
    source_uri: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(String(500), default="")
    content_md: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    collection: Mapped[PptSourceCollection] = relationship(back_populates="documents")
    chunks: Mapped[list["PptSourceChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class PptSourceChunk(Base):
    __tablename__ = "ppt_source_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("ppt_source_documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content_md: Mapped[str] = mapped_column(Text, default="")
    embedding_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    document: Mapped[PptSourceDocument] = relationship(back_populates="chunks")


class PptAgentRun(Base):
    __tablename__ = "ppt_agent_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("ppt_pages.id", ondelete="SET NULL"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="queued")
    decision_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    project: Mapped[PptProject] = relationship(back_populates="runs")


class PptAgentEvent(Base):
    __tablename__ = "ppt_agent_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("ppt_agent_runs.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    project: Mapped[PptProject] = relationship(back_populates="events")


class PptProviderConfig(Base):
    __tablename__ = "ppt_provider_configs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    base_url: Mapped[str] = mapped_column(String(500), default="https://api.deepseek.com")
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(160), default="deepseek-v4-flash")
    embedding_model: Mapped[str] = mapped_column(String(160), default="")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class PptExportJob(Base):
    __tablename__ = "ppt_export_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    project: Mapped[PptProject] = relationship(back_populates="exports")


class PptGenerationJob(Base):
    __tablename__ = "ppt_generation_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(40), default="queued")
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    completed_pages: Mapped[int] = mapped_column(Integer, default=0)
    failed_pages: Mapped[int] = mapped_column(Integer, default=0)
    current_page_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    planner_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    project: Mapped[PptProject] = relationship()
