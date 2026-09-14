"""Celery application configuration.

Celery is an optional import for source checkouts and unit tests.  Production
installs include the dependency and run the worker against Redis.
"""

from app.core.config import settings

try:  # pragma: no cover - exercised by worker processes
    from celery import Celery
except ImportError:  # pragma: no cover - normal lightweight test environment
    Celery = None  # type: ignore[assignment,misc]

try:  # pragma: no cover - optional redis transport in lightweight checkouts
    import redis  # noqa: F401
except ImportError:
    redis = None  # type: ignore[assignment]


celery_app = None
if Celery is not None and redis is not None and settings.task_queue_enabled:
    celery_app = Celery(
        "hku_edu",
        broker=settings.task_broker_url,
        backend=settings.task_result_backend,
        include=["app.jobs.tasks"],
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        broker_connection_retry_on_startup=True,
        task_always_eager=settings.task_queue_eager,
        task_eager_propagates=True,
        beat_schedule={
            "republish-task-outbox": {
                "task": "hku.system.republish_outbox",
                "schedule": 15.0,
            },
        },
    )
