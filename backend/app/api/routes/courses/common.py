from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.core.config import settings
from app.models import Course, CourseChapter, CourseMaterial, CourseMaterialIngestion, CourseSchedule, DiscussionComment, DiscussionLike, Enrollment, FileAsset, User, UserRole, FileProcessingDocument, FileProcessingJob
from app.schemas import (
    CourseChapterCreate,
    CourseChapterOut,
    CourseChapterUpdate,
    CourseCreate,
    CourseMaterialOut,
    CourseOut,
    DiscussionAuthorOut,
    DiscussionCommentCreate,
    DiscussionCommentOut,
    DiscussionLikeOut,
    ParticipantDetailOut,
    ParticipantSummaryOut,
    ScheduleIn,
)
from app.storage import LocalStorage
from app.services.file_processing import upload_asset, bind_document, ensure_document_for_asset, enqueue_job

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _course_for_user(course_id: str, user: User, db: Session, manage: bool = False) -> Course:
    course = db.scalar(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.enrollments), selectinload(Course.chapters).selectinload(CourseChapter.materials).selectinload(CourseMaterial.file_asset))
    )
    if not course:
        raise HTTPException(404, "Course not found")
    if user.role == UserRole.admin:
        return course
    if user.role == UserRole.teacher:
        if course.teacher_id != user.id:
            raise HTTPException(403, "Course access denied")
        return course
    if manage or not any(enrollment.student_id == user.id for enrollment in course.enrollments):
        raise HTTPException(403, "You are not enrolled in this course")
    return course


def _chapter_or_404(course: Course, chapter_id: str) -> CourseChapter:
    chapter = next((item for item in course.chapters if item.id == chapter_id), None)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    return chapter


def _material_out(material: CourseMaterial, db: Session) -> CourseMaterialOut:
    asset = material.file_asset
    ingestion = getattr(material, "ingestion", None)
    processing_document = db.scalar(select(FileProcessingDocument).where((FileProcessingDocument.file_asset_id == asset.id) | (FileProcessingDocument.sha256 == asset.sha256))) if asset is not None else None
    job = db.scalar(select(FileProcessingJob).where(FileProcessingJob.document_id == processing_document.id).order_by(FileProcessingJob.created_at.desc())) if processing_document else None
    return CourseMaterialOut(
        id=material.id,
        title=material.title,
        file_name=asset.original_name,
        mime_type=asset.mime_type,
        extension=asset.extension,
        size_bytes=asset.size_bytes,
        uploaded_at=material.created_at,
        download_url=f"/api/courses/{material.chapter.course_id}/materials/{material.id}/download",
        processing_status=processing_document.status if processing_document else (ingestion.status if ingestion else "pending"),
        processing_error=processing_document.error_message if processing_document else (ingestion.error_message if ingestion else None),
        document_id=processing_document.id if processing_document else None,
        job_id=job.id if job else None,
        processing_parser=processing_document.parser if processing_document else None,
        processing_fallback_reason=processing_document.error_message if processing_document and processing_document.status == "partial_ready" else None,
    )


def _chapter_out(chapter: CourseChapter, db: Session) -> CourseChapterOut:
    return CourseChapterOut(
        id=chapter.id,
        kind=chapter.kind,
        title=chapter.title,
        sort_order=chapter.sort_order,
        material_count=len(chapter.materials),
        materials=[_material_out(material, db) for material in chapter.materials],
    )


def _normalize_chapter_order(course: Course, kind: str, selected: CourseChapter | None = None, requested_order: int | None = None) -> None:
    chapters = sorted((item for item in course.chapters if item.kind == kind and item is not selected), key=lambda item: (item.sort_order, item.created_at, item.id))
    if selected is not None:
        index = len(chapters) if requested_order is None else min(max(requested_order, 0), len(chapters))
        chapters.insert(index, selected)
    for index, chapter in enumerate(chapters):
        chapter.sort_order = index


def _discussion_author_out(user: User) -> DiscussionAuthorOut:
    return DiscussionAuthorOut(id=user.id, username=user.username, name=user.name, avatar_url=user.avatar_url)


def _discussion_comment_out(comment: DiscussionComment, current_user_id: str) -> DiscussionCommentOut:
    replies = sorted(comment.replies, key=lambda item: (item.created_at, item.id))
    return DiscussionCommentOut(
        id=comment.id,
        course_id=comment.course_id,
        parent_id=comment.parent_id,
        author=_discussion_author_out(comment.author),
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        like_count=len(comment.likes),
        liked_by_me=any(like.user_id == current_user_id for like in comment.likes),
        reply_count=len(replies),
        replies=[_discussion_comment_out(reply, current_user_id) for reply in replies],
    )


def _discussion_comment_or_404(course_id: str, comment_id: str, db: Session) -> DiscussionComment:
    comment = db.scalar(
        select(DiscussionComment)
        .where(DiscussionComment.id == comment_id, DiscussionComment.course_id == course_id)
        .options(selectinload(DiscussionComment.author), selectinload(DiscussionComment.likes), selectinload(DiscussionComment.replies))
    )
    if not comment:
        raise HTTPException(404, "Discussion comment not found")
    return comment


def _discussion_activity(comment: DiscussionComment):
    timestamps = [comment.updated_at, *(reply.updated_at for reply in comment.replies)]
    return max(timestamps)


# Sub-route modules use a wildcard import intentionally so the shared
# permission and serialization helpers remain private to the package while
# still being available to each route group.
__all__ = [name for name in globals() if not name.startswith("__")]


