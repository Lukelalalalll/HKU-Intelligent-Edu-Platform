"""Stable v2 task-oriented PPT API.

The legacy `/api/ppt` router remains available during migration.  This module
exposes long-running operations with explicit 202 responses and a consistent
job envelope so new clients do not depend on implementation details.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas.ppt import ExportIn
from app.services.ppt.export_service import ExportService
from app.services.ppt.generation_service import GenerationService


router = APIRouter(prefix="/api/v2/ppt", tags=["ppt-v2"])
teacher = Depends(require_roles(UserRole.teacher))


def generation_svc(db: Session = Depends(get_db), user: User = teacher) -> GenerationService:
    return GenerationService(db, user)

def export_svc(db: Session = Depends(get_db), user: User = teacher) -> ExportService:
    return ExportService(db, user)


def _job_envelope(job: dict) -> dict:
    return {"job_id": job.get("id"), "status": "queued"}


@router.post("/projects/{project_id}/generation", status_code=status.HTTP_202_ACCEPTED)
def start_generation(project_id: str, service: GenerationService = Depends(generation_svc)):
    return _job_envelope(service.start_generation(project_id))


@router.post("/projects/{project_id}/visual-research", status_code=status.HTTP_202_ACCEPTED)
def start_visual_research(project_id: str, service: GenerationService = Depends(generation_svc)):
    return _job_envelope(service.start_visual_research(project_id))


@router.get("/projects/{project_id}/jobs/{job_id}")
def get_job(project_id: str, job_id: str, service: GenerationService = Depends(generation_svc)):
    return service.generation_job(project_id, job_id)


@router.post("/projects/{project_id}/exports", status_code=status.HTTP_202_ACCEPTED)
def start_export(project_id: str, payload: ExportIn, service: ExportService = Depends(export_svc)):
    return service.enqueue(project_id, payload.filename)
