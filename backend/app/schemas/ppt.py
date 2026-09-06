from typing import Any, Literal

from pydantic import BaseModel, Field


Stage = Literal["init", "outline", "visual", "search", "theme", "layout", "draft", "design", "export"]
Status = Literal["empty", "ready", "running", "confirmed", "stale", "failed"]


class ProviderConfigIn(BaseModel):
    base_url: str = Field(default="https://api.deepseek.com", min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)
    model: str = Field(default="deepseek-v4-flash", min_length=1, max_length=160)
    embedding_model: str = Field(default="", max_length=160)
    timeout_seconds: int = Field(default=120, ge=10, le=600)


class ProviderConfigOut(BaseModel):
    base_url: str
    api_key_configured: bool
    api_key_masked: str
    model: str
    embedding_model: str
    timeout_seconds: int


class ProjectCreateIn(BaseModel):
    title: str = Field(default="未命名课件", max_length=200)
    request_text: str = Field(min_length=1, max_length=20000)
    course_id: str | None = None


class ProjectPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    request_text: str | None = Field(default=None, max_length=20000)


class RequirementPatchIn(BaseModel):
    page_count_target: int | None = Field(default=None, ge=3, le=80)
    answers: dict[str, Any] = Field(default_factory=dict)


class RequirementChatIn(BaseModel):
    """One turn in the project-scoped requirements interview."""
    content: str | None = Field(default=None, max_length=20000)
    option_id: str | None = Field(default=None, max_length=200)
    option_label: str | None = Field(default=None, max_length=500)
    bootstrap: bool = False


class RequirementChatOut(BaseModel):
    project_id: str
    message: dict[str, Any]
    status: str
    answers: dict[str, Any]
    question: dict[str, Any] | None = None
    ready_to_outline: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    suggested_additions: list[str] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class OutlineGenerateIn(BaseModel):
    page_count_target: int = Field(default=10, ge=3, le=80)


class ThemeSelectIn(BaseModel):
    theme_id: str = Field(min_length=1, max_length=120)


class LayoutAssignmentsIn(BaseModel):
    assignments: dict[str, str] = Field(default_factory=dict)
    mode: str = Field(default="manual", pattern="^(manual|auto)$")


class PagePatchIn(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    bullets: list[str] = Field(default_factory=list, max_length=8)
    section_title: str | None = Field(default=None, max_length=200)
    speaker_notes: str | None = None


class VisualSelectionIn(BaseModel):
    asset_ids: list[str] = Field(default_factory=list, max_length=6)


class DocumentPatchIn(BaseModel):
    document: dict[str, Any]
    revision: int = Field(default=1, ge=1)


class StoryboardPatchIn(BaseModel):
    page_ids: list[str] = Field(min_length=1, max_length=80)


class CheckpointConfirmIn(BaseModel):
    note: str | None = Field(default=None, max_length=5000)


class SummaryPatchIn(BaseModel):
    summary_md: str = Field(max_length=50000)


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    page_id: str | None = None
    ui_surface: str = "search"
    option_id: str | None = Field(default=None, max_length=200)
    option_label: str | None = Field(default=None, max_length=500)


class ActionIn(BaseModel):
    action_type: str
    replace_existing: bool = True


class BatchIn(BaseModel):
    action_type: Literal["project_batch_search", "project_batch_visual", "project_batch_summary", "project_batch_draft", "project_batch_design"]


class ExportIn(BaseModel):
    filename: str | None = Field(default=None, max_length=120)
