from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import Base, engine
from app.db.session import SessionLocal
from app.api.routes import agent, assignments, auth, courses, files, teacher, student, ppt, profile, live_class, courseware_agent, lesson_plan, admin_ai
from app.models import *  # noqa: F401,F403
from app.services.ai_gateway import ensure_ai_defaults

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Resume jobs left queued/running by a development-server restart.
    db = SessionLocal()
    try:
        ensure_ai_defaults(db)
        from sqlalchemy import select
        from app.services.ppt_agent import generation_executor, _run_generation_job
        for job in db.scalars(select(PptGenerationJob).where(PptGenerationJob.status.in_(["queued", "running"]))):
            project = db.get(PptProject, job.project_id)
            if project:
                generation_executor.submit(_run_generation_job, job.id, project.id, project.owner_id)
    finally:
        db.close()
    yield

app = FastAPI(title="HKU Intelligent Edu Platform", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(assignments.router)
app.include_router(files.router)
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
