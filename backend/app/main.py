from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import Base, engine
from app.db.session import SessionLocal
from app.api.routes import agent, assignments, auth, courses, files, file_processing, teacher, student, ppt, profile, live_class, courseware_agent, lesson_plan, admin_ai
from app.models import *  # noqa: F401,F403
from app.services.ai_gateway import ensure_ai_defaults
from app.services.file_processing import recover_jobs

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Resume jobs left queued/running by a development-server restart.
    db = SessionLocal()
    try:
        ensure_ai_defaults(db)
        recover_jobs()
        from app.jobs.dispatcher import recover_outbox
        recover_outbox()
        from sqlalchemy import select
        from app.jobs.dispatcher import dispatch
        for job in db.scalars(select(PptGenerationJob).where(PptGenerationJob.status.in_(["queued", "running"]))):
            project = db.get(PptProject, job.project_id)
            if project:
                dispatch("ppt_generation", job.id, project.id, project.owner_id, task_id=f"ppt-generation:{job.id}")
    finally:
        db.close()
    yield

app = FastAPI(title="HKU Intelligent Edu Platform", version="0.1.0", lifespan=lifespan)
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
app.include_router(profile.router)
app.include_router(live_class.router)
app.include_router(live_class.webhook_router)
app.include_router(courseware_agent.router)
app.include_router(lesson_plan.router)
app.include_router(admin_ai.router)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/readyz")
def readyz():
    import sys
    import shutil
    mineru = shutil.which(settings.file_processing_mineru_command) is not None or (Path(sys.executable).with_name("mineru.exe").exists() if settings.file_processing_mineru_command.lower() == "mineru" else False)
    if settings.file_processing_require_mineru and not mineru:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="MinerU is required but not available")
    return {"status": "ready", "mineru": mineru}
