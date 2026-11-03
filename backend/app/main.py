"""FastAPI application entrypoint.

This module only owns process-level concerns: startup recovery of committed
background work, the provider-error to HTTP mapping, CORS and router
registration.  Schema changes belong to Alembic; request handling belongs to
the route modules.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.api.routes import agent, assignments, auth, courses, files, files_v2, file_processing, teacher, student, ppt, ppt_v2, profile, live_class, courseware_agent, lesson_plan, admin_ai, teacher_video
# Importing the package registers every mapper before recovery opens a session.
import app.models as _models  # noqa: F401
from app.services.ai_gateway import ensure_ai_defaults
from app.services.file_processing import recover_jobs
from app.services.provider_contract import ProviderError

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup recovery before the process accepts traffic.

    Startup re-applies provider defaults, requeues file-processing jobs and
    republishes outbox rows that were left pending.  The session opened here
    is closed before the first request is served.
    """
    # Schema creation belongs to Alembic.  The API process only performs
    # lightweight recovery of work that was committed before a restart.
    db = SessionLocal()
    try:
        ensure_ai_defaults(db)
        recover_jobs()
        from app.jobs.dispatcher import recover_outbox, recover_stale_jobs
        # Expired leases are released first so their rows become eligible for
        # the republish pass that follows.
        recover_stale_jobs()
        recover_outbox()
    finally:
        db.close()
    yield

app = FastAPI(title="HKU Intelligent Edu Platform", version="0.1.0", lifespan=lifespan)


@app.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError):
    """Map provider failures to problem-details JSON with a retry hint.

    Retryable failures return 503 so clients and workers can back off;
    non-retryable ones return 502 because repeating the call will not help.
    """
    status_code = 503 if getattr(exc, "retryable", False) else 502
    return JSONResponse(status_code=status_code, content={"type": "about:blank", "title": type(exc).__name__, "detail": str(exc), "retryable": bool(getattr(exc, "retryable", False))})


app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(assignments.router)
app.include_router(files.router)
app.include_router(file_processing.router)
app.include_router(teacher.router)
app.include_router(student.router)
app.include_router(agent.router)
app.include_router(ppt.router)
app.include_router(ppt_v2.router)
app.include_router(files_v2.router)
app.include_router(profile.router)
app.include_router(live_class.router)
app.include_router(live_class.webhook_router)
app.include_router(courseware_agent.router)
app.include_router(lesson_plan.router)
app.include_router(admin_ai.router)
app.include_router(teacher_video.router)
app.include_router(teacher_video.webhook_router)

@app.get("/healthz")
def healthz():
    """Report process liveness without touching any dependency."""
    return {"status": "ok", "service": "backend"}

@app.get("/readyz")
def readyz():
    """Report readiness for database, storage, MinerU and the task broker.

    The storage probe writes and deletes a file under the upload root, so a
    read-only volume fails readiness here instead of failing the first upload.

    Raises:
        HTTPException: 503 carrying the per-check result when a required
            dependency is unavailable.
    """
    import shutil
    from fastapi import HTTPException

    # The broker starts as healthy: deployments that leave the queue disabled
    # must not become permanently unready.
    checks = {"database": False, "storage": False, "mineru": False, "broker": True}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    try:
        settings.upload_path.mkdir(parents=True, exist_ok=True)
        probe = settings.upload_path / ".readyz"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks["storage"] = True
    except OSError:
        pass
    checks["mineru"] = shutil.which(settings.file_processing_mineru_command) is not None
    if settings.task_queue_enabled:
        try:
            from app.jobs.celery_app import celery_app
            if celery_app is not None:
                connection = celery_app.connection()
                connection.ensure_connection(max_retries=0)
                connection.release()
        except Exception:
            checks["broker"] = False
    # MinerU is only a hard requirement when document parsing is expected to
    # work in this deployment.
    required = ["database", "storage"] + (["mineru"] if settings.file_processing_require_mineru else [])
    if not all(checks[name] for name in required) or not checks["broker"]:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})
    return {"status": "ready", "checks": checks}
