"""Background task handlers.

Handlers live outside the HTTP layer so workers never import FastAPI routes.
Each handler opens its own short-lived database session and treats the
persisted job row as the source of truth.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import PptAgentEvent, PptExportJob, PptProject


def run_ppt_export(export_id: str, project_id: str, filename: str | None = None) -> None:
    from app.services.ppt_export import export_project_pptx

    db = SessionLocal()
    try:
        job = db.get(PptExportJob, export_id)
        project = db.get(PptProject, project_id)
        if not job or not project or job.status in {"completed", "canceled"}:
            return
        job.status = "running"
        db.add(PptAgentEvent(project_id=project_id, event_type="export.started", payload_json={"job_id": export_id}))
        db.commit()

        path = settings.ppt_storage_path / f"{project.id}-{export_id}.pptx"
        export_project_pptx(project, path, filename)
        job.status = "completed"
        job.file_path = str(path)
        project.current_stage = "export"
        db.add(PptAgentEvent(project_id=project_id, event_type="export.completed", payload_json={"job_id": export_id}))
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(PptExportJob, export_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:4000]
            db.add(PptAgentEvent(project_id=project_id, event_type="export.failed", payload_json={"job_id": export_id, "error": str(exc)[:500]}))
            db.commit()
    finally:
        db.close()
