from pathlib import Path
from sqlalchemy import select
from app.models import PptExportJob
from app.jobs.manager import JobManager
from .services_base import PptServiceBase

class ExportService(PptServiceBase):
    """PPT export job lifecycle; rendering remains in the worker handler."""
    def enqueue(self, project_id, filename=None):
        project = self._app.project(project_id)
        active = self.db.scalar(select(PptExportJob).where(PptExportJob.project_id == project.id, PptExportJob.status.in_(["queued", "running"])).order_by(PptExportJob.created_at.desc()))
        if active: return {"job_id": active.id, "status": active.status}
        job = PptExportJob(project_id=project.id, status="queued")
        self.db.add(job); self.db.flush()
        task_id = f"ppt-export:{project.id}"
        job.queue_task_id = task_id
        JobManager(self.db).enqueue("ppt_export", (job.id, project.id, filename), task_id)
        return {"job_id": job.id, "status": "queued"}
    def get(self, project_id, export_id):
        self._app.project(project_id)
        return self.db.scalar(select(PptExportJob).where(PptExportJob.id == export_id, PptExportJob.project_id == project_id))
