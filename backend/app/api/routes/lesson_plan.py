"""Lesson plan agent routes: projects, materials, chat, generation and export.

Every endpoint is teacher-only.  Handlers stay thin: the workflow lives in
:class:`app.services.lesson_plan.LessonPlanService`, while this module owns
HTTP concerns (status codes, streaming, file responses).
"""

import asyncio
import json
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import select

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import LessonPlanEvent, User, UserRole
from app.schemas.lesson_plan import (
    ChatIn,
    ExportIn,
    GenerateIn,
    PageDocumentIn,
    ProjectCreateIn,
    RegeneratePageIn,
)
from app.services.lesson_plan import LessonPlanService

router = APIRouter(prefix="/api/lesson-plans", tags=["lesson-plans"])
teacher = Depends(require_roles(UserRole.teacher))


def svc(db=Depends(get_db), user: User = teacher) -> LessonPlanService:
    """Build the service bound to the request session and teacher."""
    return LessonPlanService(db, user)


@router.get("/capabilities")
def capabilities(service: LessonPlanService = Depends(svc)) -> dict:
    """Report whether the lesson-plan business has a usable AI model."""
    return service.capabilities()


# List the caller's projects, most recently updated first.
@router.get("/projects")
def list_projects(service: LessonPlanService = Depends(svc)) -> dict:
    """List the caller's lesson plan projects."""
    return {"items": service.list_projects()}


# Create an empty lesson plan project.
@router.post("/projects", status_code=201)
def create_project(payload: ProjectCreateIn, service: LessonPlanService = Depends(svc)) -> dict:
    """Create a project from the teacher's brief."""
    return service.create(payload.title, payload.request_text, payload.course_id)


@router.get("/projects/{project_id}")
def get_project(project_id: str, service: LessonPlanService = Depends(svc)) -> dict:
    """Return one project summary."""
    project = service.project(project_id)
    return service.serialize(project)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, service: LessonPlanService = Depends(svc)) -> dict:
    """Delete a project owned by the caller."""
    return service.delete(project_id)


@router.get("/projects/{project_id}/state")
def project_state(project_id: str, service: LessonPlanService = Depends(svc)) -> dict:
    """Return the complete workspace state in one request."""
    return service.state(project_id)


@router.get("/projects/{project_id}/pages")
def pages(project_id: str, service: LessonPlanService = Depends(svc)) -> dict:
    """List page documents in display order."""
    return {"items": service.list_pages(project_id)}


@router.post("/projects/{project_id}/files", status_code=201)
def upload_file(project_id: str, file: UploadFile = File(...), service: LessonPlanService = Depends(svc)) -> dict:
    """Store one uploaded material and extract its text for the conversation."""
    return service.add_file(project_id, file)


@router.delete("/projects/{project_id}/files/{asset_id}")
def delete_file(project_id: str, asset_id: str, service: LessonPlanService = Depends(svc)) -> dict:
    """Remove one material from the project corpus."""
    return service.delete_file(project_id, asset_id)


@router.get("/projects/{project_id}/assets/{asset_id}")
def download_asset(project_id: str, asset_id: str, service: LessonPlanService = Depends(svc)):
    """Serve an uploaded material after ownership checks."""
    path = service.asset_path(project_id, asset_id)
    return FileResponse(path, filename=Path(path).name, media_type="application/octet-stream")


@router.post("/projects/{project_id}/chat/stream")
def chat_stream(project_id: str, payload: ChatIn, service: LessonPlanService = Depends(svc)):
    """Stream one interview/refinement turn as server-sent events."""
    service.project(project_id)

    def event_stream():
        try:
            yield f"data: {json.dumps({'type': 'status', 'status': '正在理解你的需求'}, ensure_ascii=False)}\n\n"
            for event in service.interview_stream(project_id, payload.content, payload.bootstrap, payload.option_label):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001 - the stream must always terminate cleanly
            service.db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)[:300]}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/projects/{project_id}/requirements/chat")
def requirements_chat(project_id: str, payload: ChatIn, service: LessonPlanService = Depends(svc)) -> dict:
    """Non-streaming interview turn kept for compatibility and tests."""
    return service.interview(project_id, payload.content, payload.bootstrap, payload.option_label)


@router.post("/projects/{project_id}/generate")
def generate(project_id: str, payload: GenerateIn | None = None, service: LessonPlanService = Depends(svc)) -> dict:
    """Generate (or replace) the lesson plan pages."""
    body = payload or GenerateIn()
    return service.generate(project_id, body.page_count, body.include_answers, body.instruction)


@router.post("/projects/{project_id}/pages/{page_id}/regenerate")
def regenerate_page(project_id: str, page_id: str, payload: RegeneratePageIn | None = None, service: LessonPlanService = Depends(svc)) -> dict:
    """Rewrite one page with an optional teacher instruction."""
    body = payload or RegeneratePageIn()
    return service.regenerate_page(project_id, page_id, body.instruction)


@router.patch("/projects/{project_id}/pages/{page_id}/document")
def patch_document(project_id: str, page_id: str, payload: PageDocumentIn, service: LessonPlanService = Depends(svc)) -> dict:
    """Replace one page document with optimistic revision checking."""
    return service.patch_page(project_id, page_id, payload.document, payload.revision)


@router.post("/projects/{project_id}/exports", status_code=202)
def export_project(project_id: str, payload: ExportIn | None = None, service: LessonPlanService = Depends(svc)) -> dict:
    """Render the project to PDF and record the export job."""
    body = payload or ExportIn()
    return service.export_pdf(project_id, body.include_answers, body.black_white)


@router.get("/projects/{project_id}/exports/{export_id}")
def export_status(project_id: str, export_id: str, service: LessonPlanService = Depends(svc)) -> dict:
    """Return the status of one export job."""
    return service.serialize_export(service.export_job(project_id, export_id))


@router.get("/projects/{project_id}/exports/{export_id}/download")
def download_export(project_id: str, export_id: str, service: LessonPlanService = Depends(svc)):
    """Download the PDF of a completed export."""
    return FileResponse(service.export_path(project_id, export_id), filename="lesson-plan.pdf", media_type="application/pdf")


@router.get("/projects/{project_id}/markdown")
def download_markdown(project_id: str, include_answers: bool = Query(default=True), service: LessonPlanService = Depends(svc)) -> Response:
    """Download the lesson plan as Markdown."""
    filename, content = service.export_markdown(project_id, include_answers)
    disposition = f"attachment; filename=\"lesson-plan.md\"; filename*=UTF-8''{quote(filename)}"
    return Response(content=content, media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": disposition})


@router.get("/projects/{project_id}/events/stream")
async def events(project_id: str, last_event_id: int = Query(0), service: LessonPlanService = Depends(svc)) -> StreamingResponse:
    """Stream new lesson plan events for a project over SSE."""
    service.project(project_id)

    async def generator():
        current = last_event_id
        for _ in range(120):
            rows = list(
                service.db.scalars(
                    select(LessonPlanEvent)
                    .where(LessonPlanEvent.project_id == project_id, LessonPlanEvent.id > current)
                    .order_by(LessonPlanEvent.id)
                )
            )
            for row in rows:
                current = row.id
                yield f"id: {row.id}\ndata: {json.dumps({'id': row.id, 'event_type': row.event_type, 'payload': row.payload_json}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(generator(), media_type="text/event-stream")
