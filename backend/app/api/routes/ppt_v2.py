"""Stable v2 task-oriented PPT API.

The legacy `/api/ppt` router remains available during migration.  This module
exposes long-running operations with explicit 202 responses and a consistent
job envelope so new clients do not depend on implementation details.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import PptExportJob, User, UserRole
from app.schemas.ppt import ExportIn
from app.services.ppt_agent import PptAgentService


router = APIRouter(prefix="/api/v2/ppt", tags=["ppt-v2"])
teacher = Depends(require_roles(UserRole.teacher))


def svc(db: Session = Depends(get_db), user: User = teacher) -> PptAgentService:
    return PptAgentService(db, user)


def _job_envelope(job: dict, *, job_type: str) -> dict:
    return {"job_id": job.get("id"), "job_type": job_type, "status": job.get("status", "queued"), "job": job}


@router.post("/projects/{project_id}/generation", status_code=status.HTTP_202_ACCEPTED)
def start_generation(project_id: str, service: PptAgentService = Depends(svc)):
    return _job_envelope(service.start_generation(project_id), job_type="ppt_generation")


@router.post("/projects/{project_id}/visual-research", status_code=status.HTTP_202_ACCEPTED)
def start_visual_research(project_id: str, service: PptAgentService = Depends(svc)):
    return _job_envelope(service.start_visual_research(project_id), job_type="ppt_visual_research")


@router.get("/projects/{project_id}/jobs/{job_id}")
def get_job(project_id: str, job_id: str, service: PptAgentService = Depends(svc)):
    return service.generation_job(project_id, job_id)


@router.post("/projects/{project_id}/exports", status_code=status.HTTP_202_ACCEPTED)
def start_export(project_id: str, payload: ExportIn, service: PptAgentService = Depends(svc)):
    project = service.project(project_id)
    active = service.db.scalar(
        select(PptExportJob).where(
            PptExportJob.project_id == project.id,
            PptExportJob.status.in_(["queued", "running"]),
        ).order_by(PptExportJob.created_at.desc())
    )
    if active:
        return {"job_id": active.id, "job_type": "ppt_export", "status": active.status}
    from app.jobs.dispatcher import stage_and_publish

    job = PptExportJob(project_id=project.id, status="queued")
    service.db.add(job)
    service.db.commit()
    service.db.refresh(job)
    task_id = f"ppt-export:{job.id}"
    job.queue_task_id = task_id
    stage_and_publish(service.db, "ppt_export", (job.id, project.id, payload.filename), task_id)
    return {"job_id": job.id, "job_type": "ppt_export", "status": job.status}
