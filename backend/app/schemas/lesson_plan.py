"""Request schemas for the lesson plan agent surface.

Free text, page counts and export options are bounded here so the service and
the model prompts can rely on sane input sizes.
"""

from typing import Any

from pydantic import BaseModel, Field


class ProjectCreateIn(BaseModel):
    """Payload for creating a lesson plan project."""
    title: str = Field(default="", max_length=200)
    request_text: str = Field(default="", max_length=20000)
    course_id: str | None = None


class ChatIn(BaseModel):
    """One interview or refinement turn."""
    content: str = Field(default="", max_length=4000)
    option_label: str | None = Field(default=None, max_length=200)
    bootstrap: bool = False


class GenerateIn(BaseModel):
    """Generation options; omitted fields fall back to the collected answers."""
    page_count: int | None = Field(default=None, ge=1, le=6)
    include_answers: bool | None = None
    instruction: str = Field(default="", max_length=2000)


class RegeneratePageIn(BaseModel):
    """Optional instruction for rewriting one page."""
    instruction: str = Field(default="", max_length=2000)


class PageDocumentIn(BaseModel):
    """Payload replacing one page document at a known revision."""
    document: dict[str, Any]
    revision: int = Field(default=1, ge=1)


class ExportIn(BaseModel):
    """PDF export options."""
    include_answers: bool = True
    black_white: bool = False


__all__ = [
    "ChatIn",
    "ExportIn",
    "GenerateIn",
    "PageDocumentIn",
    "ProjectCreateIn",
    "RegeneratePageIn",
]
