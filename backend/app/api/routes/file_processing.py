from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import Assignment, Course, Enrollment, FileAsset, FileContextBinding, FileProcessingDocument, FileProcessingJob, Submission, User
from app.services.file_processing import enqueue_job

router = APIRouter(prefix="/api/file-processing", tags=["file-processing"])


def _allowed(document: FileProcessingDocument, user: User, db: Session) -> bool:
    if user.role.value == "admin": return True
    if db.scalar(select(FileAsset.id).where(FileAsset.id == document.file_asset_id, FileAsset.uploader_id == user.id)) is not None:
        return True
    bindings = db.scalars(select(FileContextBinding).where(FileContextBinding.document_id == document.id)).all()
    for binding in bindings:
        if binding.owner_id == user.id and binding.visibility in {"owner", "private", "course"}:
            return True
        if binding.target_type == "submission" and binding.target_id:
            assignment_teacher = db.scalar(select(Course.teacher_id).join(Assignment, Assignment.course_id == Course.id).join(Submission, Submission.assignment_id == Assignment.id).where(Submission.id == binding.target_id))
            if assignment_teacher == user.id:
                return True
        if binding.visibility != "course" or not binding.course_id:
            continue
        course = db.get(Course, binding.course_id)
        if course and course.teacher_id == user.id:
            return True
        if db.scalar(select(Enrollment.id).where(Enrollment.course_id == binding.course_id, Enrollment.student_id == user.id)):
            return True
    return False


def _document_out(document: FileProcessingDocument, db: Session):
    job = db.scalar(select(FileProcessingJob).where(FileProcessingJob.document_id == document.id).order_by(FileProcessingJob.created_at.desc()))
    return {"id": document.id, "file_asset_id": document.file_asset_id, "filename": document.filename, "extension": document.extension, "mime_type": document.mime_type, "sha256": document.sha256, "status": document.status, "parser": document.parser, "page_count": document.page_count, "error_message": document.error_message, "manifest": document.manifest_json or {}, "job": {"id": job.id, "status": job.status, "stage": job.stage, "progress": job.progress, "processed_pages": job.processed_pages, "total_pages": job.total_pages, "error_message": job.error_message} if job else None}


@router.get("/documents/{document_id}")
def get_document(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    document = db.get(FileProcessingDocument, document_id)
    if not document or not _allowed(document, user, db): raise HTTPException(404, "Document not found")
    return _document_out(document, db)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(FileProcessingJob, job_id)
    if not job or not job.document or not _allowed(job.document, user, db): raise HTTPException(404, "Job not found")
    return {"id": job.id, "document_id": job.document_id, "status": job.status, "stage": job.stage, "progress": job.progress, "processed_pages": job.processed_pages, "total_pages": job.total_pages, "attempts": job.attempts, "error_message": job.error_message}


@router.post("/jobs/{job_id}:retry")
def retry_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(FileProcessingJob, job_id)
    if not job or not job.document or not _allowed(job.document, user, db): raise HTTPException(404, "Job not found")
    job.status = "queued"; job.stage = "queued"; job.attempts = 0; job.progress = 0; job.processed_pages = 0; job.finished_at = None; job.error_message = None; job.document.status = "queued"; job.document.error_message = None; db.commit(); enqueue_job(job.id)
    return get_job(job.id, user, db)


@router.get("/documents/{document_id}/artifacts/{name:path}")
def artifact(document_id: str, name: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    document = db.get(FileProcessingDocument, document_id)
    if not document or not _allowed(document, user, db): raise HTTPException(404, "Artifact not found")
    root = Path(document.artifact_dir).resolve(); path = (root / name).resolve()
    if root not in path.parents and path != root or not path.is_file(): raise HTTPException(404, "Artifact not found")
    return FileResponse(path)
