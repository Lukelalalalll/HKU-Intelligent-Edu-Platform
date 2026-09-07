from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.core.config import settings
from app.models import Course, CourseChapter, CourseMaterial, CourseSchedule, DiscussionComment, DiscussionLike, Enrollment, FileAsset, User, UserRole
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


def _material_out(material: CourseMaterial) -> CourseMaterialOut:
    asset = material.file_asset
    return CourseMaterialOut(
        id=material.id,
        title=material.title,
        file_name=asset.original_name,
        mime_type=asset.mime_type,
        extension=asset.extension,
        size_bytes=asset.size_bytes,
        uploaded_at=material.created_at,
        download_url=f"/api/courses/{material.chapter.course_id}/materials/{material.id}/download",
    )


def _chapter_out(chapter: CourseChapter) -> CourseChapterOut:
    return CourseChapterOut(
        id=chapter.id,
        kind=chapter.kind,
        title=chapter.title,
        sort_order=chapter.sort_order,
        material_count=len(chapter.materials),
        materials=[_material_out(material) for material in chapter.materials],
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


@router.get("/{course_id}/discussion", response_model=list[DiscussionCommentOut])
def list_discussion(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _course_for_user(course_id, user, db)
    comments = db.scalars(
        select(DiscussionComment)
        .where(DiscussionComment.course_id == course_id, DiscussionComment.parent_id.is_(None))
        .options(
            selectinload(DiscussionComment.author),
            selectinload(DiscussionComment.likes),
            selectinload(DiscussionComment.replies).selectinload(DiscussionComment.author),
            selectinload(DiscussionComment.replies).selectinload(DiscussionComment.likes),
        )
    ).all()
    comments.sort(key=lambda item: (_discussion_activity(item), item.id), reverse=True)
    return [_discussion_comment_out(comment, user.id) for comment in comments]


@router.post("/{course_id}/discussion", response_model=DiscussionCommentOut, status_code=201)
def create_discussion_comment(course_id: str, payload: DiscussionCommentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _course_for_user(course_id, user, db)
    comment = DiscussionComment(course_id=course_id, author_id=user.id, content=payload.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment.author = user
    return _discussion_comment_out(comment, user.id)


@router.post("/{course_id}/discussion/{comment_id}/replies", response_model=DiscussionCommentOut, status_code=201)
def create_discussion_reply(course_id: str, comment_id: str, payload: DiscussionCommentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _course_for_user(course_id, user, db)
    parent = _discussion_comment_or_404(course_id, comment_id, db)
    if parent.parent_id is not None:
        raise HTTPException(400, "Replies can only target top-level comments")
    reply = DiscussionComment(course_id=course_id, author_id=user.id, parent_id=parent.id, content=payload.content)
    db.add(reply)
    db.commit()
    db.refresh(reply)
    reply.author = user
    return _discussion_comment_out(reply, user.id)


@router.put("/{course_id}/discussion/{comment_id}/like", response_model=DiscussionLikeOut)
def like_discussion_comment(course_id: str, comment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _course_for_user(course_id, user, db)
    comment = _discussion_comment_or_404(course_id, comment_id, db)
    like = db.scalar(select(DiscussionLike).where(DiscussionLike.comment_id == comment.id, DiscussionLike.user_id == user.id))
    if not like:
        db.add(DiscussionLike(comment_id=comment.id, user_id=user.id))
        db.commit()
    count = db.scalar(select(func.count(DiscussionLike.id)).where(DiscussionLike.comment_id == comment.id)) or 0
    return DiscussionLikeOut(liked=True, like_count=count)


@router.delete("/{course_id}/discussion/{comment_id}/like", response_model=DiscussionLikeOut)
def unlike_discussion_comment(course_id: str, comment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _course_for_user(course_id, user, db)
    comment = _discussion_comment_or_404(course_id, comment_id, db)
    like = db.scalar(select(DiscussionLike).where(DiscussionLike.comment_id == comment.id, DiscussionLike.user_id == user.id))
    if like:
        db.delete(like)
        db.commit()
    count = db.scalar(select(func.count(DiscussionLike.id)).where(DiscussionLike.comment_id == comment.id)) or 0
    return DiscussionLikeOut(liked=False, like_count=count)


@router.delete("/{course_id}/discussion/{comment_id}", status_code=204)
def delete_discussion_comment(course_id: str, comment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db)
    comment = _discussion_comment_or_404(course_id, comment_id, db)
    if comment.author_id != user.id and user.role not in {UserRole.admin} and course.teacher_id != user.id:
        raise HTTPException(403, "You cannot delete this comment")
    db.delete(comment)
    db.commit()


@router.get("/{course_id}/materials", response_model=list[CourseChapterOut])
def list_materials(course_id: str, kind: str = Query(..., pattern="^(lecture|tutorial)$"), user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db)
    return [_chapter_out(chapter) for chapter in sorted((item for item in course.chapters if item.kind == kind), key=lambda item: item.sort_order)]


@router.post("/{course_id}/materials/chapters", response_model=CourseChapterOut, status_code=201)
def create_material_chapter(course_id: str, payload: CourseChapterCreate, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    title = payload.title.strip()
    if any(item.kind == payload.kind and item.title.casefold() == title.casefold() for item in course.chapters):
        raise HTTPException(409, "Chapter title already exists")
    chapter = CourseChapter(course_id=course.id, kind=payload.kind, title=title, sort_order=len([item for item in course.chapters if item.kind == payload.kind]))
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return _chapter_out(chapter)


@router.patch("/{course_id}/materials/chapters/{chapter_id}", response_model=CourseChapterOut)
def update_material_chapter(course_id: str, chapter_id: str, payload: CourseChapterUpdate, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    chapter = _chapter_or_404(course, chapter_id)
    if payload.title is not None:
        title = payload.title.strip()
        if any(item.id != chapter.id and item.kind == chapter.kind and item.title.casefold() == title.casefold() for item in course.chapters):
            raise HTTPException(409, "Chapter title already exists")
        chapter.title = title
    _normalize_chapter_order(course, chapter.kind, chapter, payload.sort_order)
    db.commit()
    db.refresh(chapter)
    return _chapter_out(chapter)


@router.delete("/{course_id}/materials/chapters/{chapter_id}")
def delete_material_chapter(course_id: str, chapter_id: str, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    chapter = _chapter_or_404(course, chapter_id)
    chapter_kind = chapter.kind
    chapter_id_value = chapter.id
    materials = list(chapter.materials)
    keys = [material.file_asset.storage_key for material in materials]
    for material in materials:
        db.delete(material)
        if material.file_asset:
            db.delete(material.file_asset)
    db.delete(chapter)
    db.commit()
    storage = LocalStorage(settings.upload_path)
    for key in keys:
        storage.delete(key)
    remaining = sorted((item for item in course.chapters if item.id != chapter_id_value and item.kind == chapter_kind), key=lambda item: (item.sort_order, item.created_at, item.id))
    for index, item in enumerate(remaining):
        item.sort_order = index
    db.commit()
    return {"message": "Chapter deleted"}


@router.post("/{course_id}/materials/chapters/{chapter_id}/files", response_model=CourseMaterialOut, status_code=201)
def upload_material(course_id: str, chapter_id: str, file: UploadFile = File(...), title: str | None = Form(default=None), user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    chapter = _chapter_or_404(course, chapter_id)
    content = file.file.read()
    storage = LocalStorage(settings.upload_path)
    key, size, digest = storage.save(file.filename or "material", content)
    asset = FileAsset(original_name=file.filename or "material", mime_type=file.content_type or "application/octet-stream", extension=Path(file.filename or "").suffix.lower(), size_bytes=size, sha256=digest, storage_key=key, uploader_id=user.id, course_id=course.id)
    material = CourseMaterial(chapter=chapter, file_asset=asset, title=(title or file.filename or "Material").strip() or "Material", uploaded_by=user.id)
    db.add_all([asset, material])
    db.commit()
    db.refresh(material)
    return _material_out(material)


@router.delete("/{course_id}/materials/{material_id}")
def delete_material(course_id: str, material_id: str, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db, manage=True)
    material = next((item for chapter in course.chapters for item in chapter.materials if item.id == material_id), None)
    if not material:
        raise HTTPException(404, "Material not found")
    key = material.file_asset.storage_key
    asset = material.file_asset
    db.delete(material)
    db.delete(asset)
    db.commit()
    LocalStorage(settings.upload_path).delete(key)
    return {"message": "Material deleted"}


@router.get("/{course_id}/materials/{material_id}/download")
def download_material(course_id: str, material_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = _course_for_user(course_id, user, db)
    material = next((item for chapter in course.chapters for item in chapter.materials if item.id == material_id), None)
    if not material:
        raise HTTPException(404, "Material not found")
    path = settings.upload_path / material.file_asset.storage_key
    if not path.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(path, media_type=material.file_asset.mime_type, filename=material.file_asset.original_name)

def serialize(course: Course) -> CourseOut:
    return CourseOut(id=course.id, code=course.code, name=course.name, description=course.description, teacher_id=course.teacher_id, academic_year_start=course.academic_year_start, semester=course.semester, timezone=course.timezone, teacher_name=course.teacher.name, enrolled_count=len(course.enrollments), schedules=[ScheduleIn.model_validate(s, from_attributes=True) for s in course.schedules])

@router.get("", response_model=list[CourseOut])
def list_courses(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.teacher:
        courses = db.scalars(select(Course).where(Course.teacher_id == user.id).order_by(Course.code)).all()
    elif user.role == UserRole.student:
        courses = db.scalars(select(Course).join(Enrollment).where(Enrollment.student_id == user.id).order_by(Course.code)).all()
    else:
        courses = db.scalars(select(Course).order_by(Course.code)).all()
    return [serialize(c) for c in courses]

@router.post("", response_model=CourseOut, status_code=201)
def create_course(payload: CourseCreate, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    if db.scalar(select(Course).where(Course.code == payload.code)):
        raise HTTPException(status_code=409, detail="Course code already exists")
    course = Course(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        teacher_id=user.id,
        academic_year_start=payload.academic_year_start,
        semester=payload.semester,
        timezone=payload.timezone,
    )
    course.schedules = [CourseSchedule(**s.model_dump()) for s in payload.schedules]
    db.add(course)
    db.commit()
    db.refresh(course)
    return serialize(course)

@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if user.role == UserRole.student and not any(e.student_id == user.id for e in course.enrollments):
        raise HTTPException(403, "You are not enrolled in this course")
    if user.role == UserRole.teacher and course.teacher_id != user.id:
        raise HTTPException(403, "Course access denied")
    return serialize(course)

@router.get("/{course_id}/participants", response_model=list[ParticipantDetailOut | ParticipantSummaryOut])
def list_participants(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = db.scalar(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.enrollments).selectinload(Enrollment.student))
    )
    if not course:
        raise HTTPException(404, "Course not found")
    if user.role == UserRole.student and not any(enrollment.student_id == user.id for enrollment in course.enrollments):
        raise HTTPException(403, "You are not enrolled in this course")
    if user.role == UserRole.teacher and course.teacher_id != user.id:
        raise HTTPException(403, "Course access denied")

    enrollments = sorted(
        (enrollment for enrollment in course.enrollments if enrollment.student.role == UserRole.student),
        key=lambda enrollment: (
            0 if user.role == UserRole.student and enrollment.student_id == user.id else 1,
            (enrollment.student.name or "").casefold(),
            enrollment.student.email.casefold(),
        ),
    )
    if user.role in {UserRole.teacher, UserRole.admin}:
        return [
            ParticipantDetailOut(
                id=enrollment.student.id,
                name=enrollment.student.name,
                email=enrollment.student.email,
                username=enrollment.student.username,
                avatar_url=enrollment.student.avatar_url,
                enrolled_at=enrollment.enrolled_at,
            ).model_dump(mode="json")
            for enrollment in enrollments
        ]
    return [
        ParticipantSummaryOut(
            id=enrollment.student.id,
            name=enrollment.student.name,
            email=enrollment.student.email,
        ).model_dump()
        for enrollment in enrollments
    ]

@router.post("/{course_id}/enroll", status_code=201)
def enroll(course_id: str, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    if not db.get(Course, course_id):
        raise HTTPException(404, "Course not found")
    if db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == user.id)):
        raise HTTPException(409, "Already enrolled")
    db.add(Enrollment(course_id=course_id, student_id=user.id))
    db.commit()
    return {"message": "Enrolled"}

@router.delete("/{course_id}/enroll")
def unenroll(course_id: str, user: User = Depends(require_roles(UserRole.student)), db: Session = Depends(get_db)):
    enrollment = db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == user.id))
    if not enrollment:
        raise HTTPException(404, "Enrollment not found")
    db.delete(enrollment)
    db.commit()
    return {"message": "Unenrolled"}
