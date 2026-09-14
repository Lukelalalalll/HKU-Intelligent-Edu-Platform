"""One dispatch surface for durable background work."""

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any
import json
from datetime import datetime, timezone

from app.jobs.celery_app import celery_app

_fallback_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hku-fallback")
_fallback_lock = Lock()
_fallback_tasks: set[str] = set()

_TASKS = {
    "file_processing": "process_file_processing_job",
    "courseware_rag": "ingest_courseware_material",
    "ppt_generation": "run_ppt_generation",
    "ppt_visual_research": "run_ppt_visual_research",
    "ppt_export": "run_ppt_export",
}


def is_queue_available() -> bool:
    return celery_app is not None


def stage_task(db, kind: str, args: tuple[Any, ...], task_id: str) -> str:
    """Write a task to the transactional outbox before the business commit."""
    from app.models import TaskOutbox

    row = db.get(TaskOutbox, task_id)
    if row is None:
        row = TaskOutbox(
            id=task_id,
            task_type=kind,
            payload_json={"args": list(args)},
            status="pending",
        )
        db.add(row)
    return task_id


def publish_task(db, task_id: str) -> str | None:
    """Publish an outbox row after its transaction has committed."""
    from app.models import TaskOutbox

    row = db.get(TaskOutbox, task_id)
    if row is None or row.status == "published":
        return task_id if row else None
    payload = row.payload_json or {}
    try:
        result = dispatch(row.task_type, *(payload.get("args") or []), task_id=row.id)
        if result is None:
            row.attempts = (row.attempts or 0) + 1
            row.last_error = "Task broker unavailable"
            db.commit()
            return None
        row.status = "published"
        row.attempts = (row.attempts or 0) + 1
        row.published_at = datetime.now(timezone.utc)
        row.last_error = None
        db.commit()
        return result
    except Exception as exc:  # pragma: no cover - defensive broker handling
        row.attempts = (row.attempts or 0) + 1
        row.last_error = str(exc)[:2000]
        db.commit()
        return None


def stage_and_publish(db, kind: str, args: tuple[Any, ...], task_id: str) -> str | None:
    """Atomically persist an outbox row, then publish it after commit."""
    # The lightweight local fallback has no broker and is intentionally used by
    # unit tests.  Do not open a second database connection in that mode: test
    # sessions are often SQLite dependency overrides.
    if celery_app is None:
        return dispatch(kind, *args, task_id=task_id)
    stage_task(db, kind, args, task_id)
    db.commit()
    return publish_task(db, task_id)


def recover_outbox() -> None:
    """Republish rows left pending by an API or broker restart."""
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models import TaskOutbox

    db = SessionLocal()
    try:
        rows = db.scalars(select(TaskOutbox).where(TaskOutbox.status != "published").order_by(TaskOutbox.created_at)).all()
        for row in rows:
            publish_task(db, row.id)
    finally:
        db.close()


def dispatch(kind: str, *args: Any, task_id: str | None = None) -> str | None:
    """Queue a task and return its broker id.

    A small local fallback keeps tests and developer checkouts usable before
    Redis/Celery are installed.  It is deliberately centralized so no domain
    service owns its own executor or duplicate de-duplication set.
    """
    task_name = _TASKS.get(kind)
    if not task_name:
        raise ValueError(f"Unknown background task: {kind}")
    if celery_app is not None:  # pragma: no cover - requires celery/redis
        from app.jobs import tasks

        task = getattr(tasks, task_name)
        try:
            result = task.apply_async(args=args, task_id=task_id)
        except Exception:
            # Broker outages must not make a committed API request fail.  The
            # database recovery pass will retry queued rows when the worker is
            # available again.
            result = None
        if result is None:
            return None
        return result.id
    from app.jobs import tasks

    fallback_id = task_id or f"local:{kind}:{id(args)}"
    with _fallback_lock:
        if fallback_id in _fallback_tasks:
            return fallback_id
        _fallback_tasks.add(fallback_id)

    def run() -> None:
        try:
            getattr(tasks, task_name)(*args)
        finally:
            with _fallback_lock:
                _fallback_tasks.discard(fallback_id)

    _fallback_executor.submit(run)
    return fallback_id
