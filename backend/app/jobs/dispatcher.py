"""One dispatch surface for durable background work."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Any
from datetime import datetime, timedelta, timezone

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
    "video_generation": "run_video_generation",
    "video_render": "run_video_render",
    "video_cleanup": "run_video_cleanup",
    "video_provider_poll": "run_video_provider_poll",
}


@dataclass(frozen=True)
class JobHandle:
    id: str
    kind: str
    status: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _retry_at(attempts: int) -> datetime:
    from app.core.config import settings

    delay = settings.task_retry_backoff_seconds * (2 ** max(0, min(attempts - 1, 8)))
    return _utcnow() + timedelta(seconds=delay)


def is_queue_available() -> bool:
    return celery_app is not None


def stage_task(db, kind: str, args: tuple[Any, ...], task_id: str) -> str:
    """Write a task to the transactional outbox before the business commit."""
    from app.models import TaskOutbox

    row = db.get(TaskOutbox, task_id)
    if row is None:
        from app.core.config import settings

        row = TaskOutbox(
            id=task_id,
            task_type=kind,
            payload_json={"args": list(args)},
            status="pending",
            max_attempts=settings.task_max_retries,
        )
        db.add(row)
    return task_id


def publish_task(db, task_id: str) -> str | None:
    """Publish an outbox row after its transaction has committed."""
    from app.models import TaskOutbox

    row = db.get(TaskOutbox, task_id)
    if row is None or row.status in {"published", "canceled"}:
        return task_id if row else None
    if row.next_run_at and row.next_run_at > _utcnow():
        return None
    payload = row.payload_json or {}
    try:
        row.status = "publishing"
        row.lease_until = _utcnow() + timedelta(seconds=60)
        db.commit()
        result = dispatch(row.task_type, *(payload.get("args") or []), task_id=row.id)
        if result is None:
            row.attempts = (row.attempts or 0) + 1
            row.last_error = "Task broker unavailable"
            row.next_run_at = _retry_at(row.attempts)
            row.status = "pending"
            row.lease_until = None
            db.commit()
            return None
        row.status = "published"
        row.attempts = (row.attempts or 0) + 1
        row.published_at = datetime.now(timezone.utc)
        row.last_error = None
        row.next_run_at = None
        row.lease_until = None
        db.commit()
        return result
    except Exception as exc:  # pragma: no cover - defensive broker handling
        row.attempts = (row.attempts or 0) + 1
        row.last_error = str(exc)[:2000]
        row.next_run_at = _retry_at(row.attempts)
        row.lease_until = None
        if row.attempts >= (row.max_attempts or 3):
            row.status = "failed"
        else:
            row.status = "pending"
        db.commit()
        return None


def stage_and_publish(db, kind: str, args: tuple[Any, ...], task_id: str) -> str | None:
    """Atomically persist an outbox row, then publish it after commit."""
    # The lightweight local fallback has no broker and is intentionally used by
    # unit tests.  Do not open a second database connection in that mode: test
    # sessions are often SQLite dependency overrides.
    if celery_app is None:
        # Persist the outbox row in the caller's session, then use the local
        # executor as the delivery mechanism.
        from app.models import TaskOutbox
        stage_task(db, kind, args, task_id)
        db.commit()
        result = dispatch(kind, *args, task_id=task_id)
        row = db.get(TaskOutbox, task_id)
        if row and result:
            row.status = "published"
            row.attempts = (row.attempts or 0) + 1
            row.published_at = datetime.now(timezone.utc)
            row.next_run_at = None
            row.lease_until = None
            db.commit()
        return result
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
        now = _utcnow()
        rows = db.scalars(
            select(TaskOutbox)
            .where(
                TaskOutbox.status.in_(["pending", "failed", "publishing"]),
                (TaskOutbox.next_run_at.is_(None) | (TaskOutbox.next_run_at <= now)),
                (TaskOutbox.lease_until.is_(None) | (TaskOutbox.lease_until <= now)),
            )
            .order_by(TaskOutbox.created_at)
        ).all()
        for row in rows:
            if row.status == "failed" and row.attempts >= (row.max_attempts or 3):
                continue
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


def enqueue(db, kind: str, payload: tuple[Any, ...], idempotency_key: str) -> JobHandle:
    """Create one durable outbox record and publish it after commit."""
    if kind not in _TASKS:
        raise ValueError(f"Unknown background task: {kind}")
    stage_task(db, kind, payload, idempotency_key)
    db.commit()
    result = publish_task(db, idempotency_key)
    from app.models import TaskOutbox

    row = db.get(TaskOutbox, idempotency_key)
    return JobHandle(id=idempotency_key, kind=kind, status="published" if result else (row.status if row else "pending"))


def cancel(db, job_id: str) -> bool:
    from app.models import TaskOutbox

    row = db.get(TaskOutbox, job_id)
    if not row or row.status == "published":
        return False
    row.status = "canceled"
    row.lease_until = None
    db.commit()
    return True


def retry(db, job_id: str) -> JobHandle:
    from app.models import TaskOutbox

    row = db.get(TaskOutbox, job_id)
    if not row:
        raise ValueError(f"Unknown task: {job_id}")
    row.status = "pending"
    row.attempts = 0
    row.next_run_at = None
    row.lease_until = None
    row.last_error = None
    db.commit()
    result = publish_task(db, job_id)
    return JobHandle(id=job_id, kind=row.task_type, status="published" if result else row.status)


def recover_stale_jobs() -> int:
    """Release expired leases and republish eligible outbox rows."""
    from app.db.session import SessionLocal
    from app.models import TaskOutbox
    from sqlalchemy import select

    db = SessionLocal()
    try:
        now = _utcnow()
        rows = db.scalars(select(TaskOutbox).where(TaskOutbox.lease_until.is_not(None), TaskOutbox.lease_until <= now)).all()
        for row in rows:
            row.lease_until = None
            if row.status == "publishing":
                row.status = "pending"
        db.commit()
        recover_outbox()
        return len(rows)
    finally:
        db.close()
