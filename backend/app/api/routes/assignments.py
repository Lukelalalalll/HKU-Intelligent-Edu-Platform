from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import Assignment, AssignmentAttachment, Course, Enrollment, FileAsset, Submission, User, UserRole
from app.schemas import AssignmentCreate, AssignmentOut, SubmissionCreate, SubmissionOut

router = APIRouter(prefix="/api/courses/{course_id}/assignments", tags=["assignments"])

@router.get("", response_model=list[AssignmentOut])
def list_assignments(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if user.role == UserRole.teacher and course.teacher_id != user.id:
        raise HTTPException(403, "Course access denied")
    if user.role == UserRole.student and not db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == user.id)):
        raise HTTPException(403, "You are not enrolled in this course")
    rows = db.scalars(select(Assignment).where(Assignment.course_id == course_id).order_by(Assignment.created_at.desc())).all()
    return [_out(x) for x in rows]

def _out(a: Assignment):
    return {"id": a.id, "course_id": a.course_id, "title": a.title, "description": a.description, "due_at": a.due_at, "max_score": a.max_score, "status": a.status, "attachments": [{"id": x.id, "file_asset_id": x.file_asset_id, "file_name": x.file_asset.original_name, "mime_type": x.file_asset.mime_type, "size_bytes": x.file_asset.size_bytes, "download_url": f"/api/courses/{a.course_id}/assignments/{a.id}/attachments/{x.id}/download"} for x in a.attachments]}

@router.post("", response_model=AssignmentOut, status_code=201)
def create_assignment(course_id: str, payload: AssignmentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if user.role != UserRole.admin and course.teacher_id != user.id:
        raise HTTPException(403, "Only the course teacher can publish assignments")
    ids = payload.file_asset_ids
    assignment = Assignment(course_id=course_id, teacher_id=user.id, **payload.model_dump(exclude={"file_asset_ids"}))
    db.add(assignment)
    for index, asset_id in enumerate(ids):
        asset = db.get(FileAsset, asset_id)
        if not asset or asset.uploader_id != user.id: raise HTTPException(404, "File asset not found")
        db.add(AssignmentAttachment(assignment=assignment, file_asset=asset, sort_order=index))
    db.commit()
    db.refresh(assignment)
    return _out(assignment)

@router.post("/{assignment_id}/attachments", status_code=201)
def add_attachment(course_id: str, assignment_id: str, file_asset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.scalar(select(Assignment).where(Assignment.id == assignment_id, Assignment.course_id == course_id))
    if not assignment or (user.role != UserRole.admin and assignment.teacher_id != user.id): raise HTTPException(404, "Assignment not found")
    asset = db.get(FileAsset, file_asset_id)
    if not asset or asset.uploader_id != user.id: raise HTTPException(404, "File asset not found")
    item = AssignmentAttachment(assignment_id=assignment.id, file_asset_id=asset.id, sort_order=len(assignment.attachments)); db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "file_asset_id": asset.id, "file_name": asset.original_name, "mime_type": asset.mime_type, "size_bytes": asset.size_bytes, "download_url": f"/api/courses/{course_id}/assignments/{assignment_id}/attachments/{item.id}/download"}

@router.delete("/{assignment_id}/attachments/{attachment_id}", status_code=204)
def remove_attachment(course_id: str, assignment_id: str, attachment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(AssignmentAttachment).join(Assignment).where(AssignmentAttachment.id == attachment_id, Assignment.id == assignment_id, Assignment.course_id == course_id))
    if not item or (user.role != UserRole.admin and item.assignment.teacher_id != user.id): raise HTTPException(404, "Attachment not found")
    db.delete(item); db.commit()

@router.get("/{assignment_id}/attachments/{attachment_id}/download")
def download_attachment(course_id: str, assignment_id: str, attachment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.scalar(select(Assignment).where(Assignment.id == assignment_id, Assignment.course_id == course_id))
    if not assignment: raise HTTPException(404, "Assignment not found")
    if user.role == UserRole.student and not db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == user.id)): raise HTTPException(403, "Not enrolled")
    item = db.scalar(select(AssignmentAttachment).where(AssignmentAttachment.id == attachment_id, AssignmentAttachment.assignment_id == assignment_id))
    if not item: raise HTTPException(404, "Attachment not found")
    path = settings.upload_path / item.file_asset.storage_key
    if not path.is_file(): raise HTTPException(404, "File not found")
    return FileResponse(path, media_type=item.file_asset.mime_type, filename=item.file_asset.original_name)

@router.post("/{assignment_id}/submissions", response_model=SubmissionOut, status_code=201)
def submit_assignment(course_id: str, assignment_id: str, payload: SubmissionCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.student:
        raise HTTPException(403, "Only students can submit assignments")
    assignment = db.scalar(select(Assignment).where(Assignment.id == assignment_id, Assignment.course_id == course_id))
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    if not db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == user.id)):
        raise HTTPException(403, "You are not enrolled in this course")
    existing = db.scalar(select(Submission).where(Submission.assignment_id == assignment_id, Submission.student_id == user.id))
    if existing:
        existing.content = payload.content
        existing.file_asset_id = payload.file_asset_id
        db.commit()
        db.refresh(existing)
        return existing
    submission = Submission(assignment_id=assignment_id, student_id=user.id, **payload.model_dump())
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission

@router.get("/{assignment_id}/submissions", response_model=list[SubmissionOut])
def list_submissions(course_id: str, assignment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.get(Assignment, assignment_id)
    if not assignment or assignment.course_id != course_id:
        raise HTTPException(404, "Assignment not found")
    if user.role != UserRole.admin and assignment.teacher_id != user.id:
        raise HTTPException(403, "Only the course teacher can view submissions")
    return db.scalars(select(Submission).where(Submission.assignment_id == assignment_id).order_by(Submission.submitted_at.desc())).all()
