"""Teacher material uploads and prompt context for lesson plans.

Uploads reuse the shared file-processing pipeline so the same bytes are parsed
once across the platform.  The lesson plan additionally extracts a text
snapshot synchronously: the interviewing and generation calls must work even
when no background worker is running in a developer checkout.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import LessonPlanAsset, LessonPlanProject, User
from app.services.file_processing import bind_document, upload_asset_stream
from app.services.file_processing.validation import validate_upload
from app.services.text_extraction import extract_text, truncate_text

MAX_STORED_TEXT = 120_000
MAX_EXCERPT_CHARS = 6_000
MAX_CONTEXT_CHARS = 12_000

# Images are deliberately out of scope for the lesson plan corpus in this
# iteration: the vision path belongs to the PPT agent.
REJECTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def project_root(project_id: str) -> Path:
    """Return the on-disk directory reserved for one project's exports."""
    return settings.ppt_storage_path / "lesson_plans" / project_id


def store_upload(db: Session, user: User, project: LessonPlanProject, upload: UploadFile) -> LessonPlanAsset:
    """Persist one upload, extract its text and return the lesson plan asset.

    Raises:
        HTTPException: 415 when validation rejects the file.
    """
    content = upload.file.read()
    try:
        name, extension = validate_upload(upload.filename, upload.content_type, len(content))
        if extension in REJECTED_SUFFIXES:
            raise ValueError("学案资料暂不支持图片，请上传 PDF、Word、PPT、Excel、Markdown 或 TXT 文件")
        asset, document, job = upload_asset_stream(
            db,
            uploader_id=user.id,
            filename=name,
            mime_type=upload.content_type,
            file=io.BytesIO(content),
            target_type="lesson_plan_project",
            target_id=project.id,
            owner_id=user.id,
            visibility="owner",
            metadata={"project_id": project.id},
        )
        bind_document(
            db,
            document.id,
            target_type="lesson_plan_project",
            target_id=project.id,
            owner_id=user.id,
            visibility="owner",
            metadata={"project_id": project.id},
        )
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc

    source_path = settings.upload_path / asset.storage_key
    text, truncated = truncate_text(extract_text(source_path, content, upload.content_type), MAX_STORED_TEXT)
    row = LessonPlanAsset(
        project_id=project.id,
        source_type="upload",
        title=name,
        file_path=str(source_path),
        metadata_json={
            "mime_type": upload.content_type or "",
            "size_bytes": len(content),
            "document_id": document.id,
            "job_id": job.id if job else None,
            "chars": len(text),
            "truncated": truncated,
            "status": "ready" if text else "empty",
            "error": "" if text else "未能从该文件抽取文本，请在对话中补充要点",
            "text": text,
        },
    )
    db.add(row)
    db.flush()
    row.public_url = f"/api/lesson-plans/projects/{project.id}/assets/{row.id}"
    db.flush()
    return row


def serialize_asset(asset: LessonPlanAsset) -> dict[str, Any]:
    """Serialize one material row without exposing the extracted text."""
    metadata = asset.metadata_json or {}
    return {
        "id": asset.id,
        "title": asset.title,
        "source_type": asset.source_type,
        "public_url": asset.public_url,
        "status": metadata.get("status") or "ready",
        "chars": int(metadata.get("chars") or 0),
        "truncated": bool(metadata.get("truncated")),
        "mime_type": metadata.get("mime_type") or "",
        "document_id": metadata.get("document_id"),
        "error": metadata.get("error") or "",
    }


def assets_for_project(db: Session, project_id: str) -> list[LessonPlanAsset]:
    """Return the project materials in upload order."""
    return list(
        db.scalars(
            select(LessonPlanAsset)
            .where(LessonPlanAsset.project_id == project_id)
            .order_by(LessonPlanAsset.id.asc())
        )
    )


def asset_by_id(db: Session, project_id: str, asset_id: str) -> LessonPlanAsset:
    """Load one asset scoped to its project.

    Raises:
        HTTPException: 404 when the asset is unknown.
    """
    asset = db.scalar(
        select(LessonPlanAsset).where(
            LessonPlanAsset.id == asset_id,
            LessonPlanAsset.project_id == project_id,
        )
    )
    if not asset:
        raise HTTPException(404, "资料不存在")
    return asset


def delete_asset(db: Session, asset: LessonPlanAsset) -> None:
    """Remove the lesson-plan reference without deleting shared file bytes."""
    from app.models import FileContextBinding

    metadata = asset.metadata_json or {}
    document_id = metadata.get("document_id")
    if document_id:
        bindings = db.scalars(
            select(FileContextBinding).where(
                FileContextBinding.document_id == document_id,
                FileContextBinding.target_type == "lesson_plan_project",
                FileContextBinding.target_id == asset.project_id,
            )
        ).all()
        for binding in bindings:
            db.delete(binding)
    db.delete(asset)


def context_materials(db: Session, project: LessonPlanProject) -> list[dict[str, Any]]:
    """Return the material excerpts injected into prompts.

    Each file contributes at most :data:`MAX_EXCERPT_CHARS`; the total prompt
    budget is capped by :data:`MAX_CONTEXT_CHARS` so one large PDF cannot crowd
    out the conversation.
    """
    output: list[dict[str, Any]] = []
    remaining = MAX_CONTEXT_CHARS
    for asset in assets_for_project(db, project.id):
        text = str((asset.metadata_json or {}).get("text") or "").strip()
        if not text or remaining <= 0:
            continue
        excerpt = text[: min(MAX_EXCERPT_CHARS, remaining)]
        remaining -= len(excerpt)
        output.append({"title": asset.title, "text": excerpt})
    return output


__all__ = [
    "MAX_CONTEXT_CHARS",
    "MAX_EXCERPT_CHARS",
    "asset_by_id",
    "assets_for_project",
    "context_materials",
    "delete_asset",
    "project_root",
    "serialize_asset",
    "store_upload",
]
