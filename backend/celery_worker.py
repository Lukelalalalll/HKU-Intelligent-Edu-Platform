"""Worker entrypoint: ``celery -A celery_worker.celery_app worker``."""

from app.jobs.celery_app import celery_app

__all__ = ["celery_app"]
