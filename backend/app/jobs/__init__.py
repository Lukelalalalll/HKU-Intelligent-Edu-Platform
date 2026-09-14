"""Background task infrastructure.

The public dispatcher intentionally hides the broker implementation from API
routes.  This keeps request handlers testable and lets local development run
without Redis while production uses Celery.
"""

from app.jobs.dispatcher import dispatch, is_queue_available

__all__ = ["dispatch", "is_queue_available"]
