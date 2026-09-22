"""Application service facade for durable background work."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.jobs.dispatcher import JobHandle, cancel, enqueue, recover_stale_jobs, retry


class JobManager:
    """Keep job lifecycle operations behind one dependency-injectable object."""

    def __init__(self, db: Session):
        self.db = db

    def enqueue(self, kind: str, payload: tuple, idempotency_key: str) -> JobHandle:
        return enqueue(self.db, kind, payload, idempotency_key)

    def cancel(self, job_id: str) -> bool:
        return cancel(self.db, job_id)

    def retry(self, job_id: str) -> JobHandle:
        return retry(self.db, job_id)

    def recover_stale_jobs(self) -> int:
        return recover_stale_jobs()
