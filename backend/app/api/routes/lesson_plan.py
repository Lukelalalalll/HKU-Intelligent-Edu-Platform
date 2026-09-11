import asyncio, json
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from app.api.deps import require_roles
from app.db.session import get_db
from app.models import User, UserRole, LessonPlanProject, LessonPlanPage, LessonPlanAsset, LessonPlanEvent
from app.services.lesson_plan import LessonPlanService
from app.core.config import settings
from app.models import LessonPlanExportJob

router = APIRouter(prefix="/api/lesson-plans", tags=["lesson-plans"])
teacher = Depends(require_roles(UserRole.teacher))

class ProjectIn(BaseModel):
    title: str = "未命名学案"
    request_text: str = ""
    course_id: str | None = None
class DocumentIn(BaseModel):
    document: dict
    revision: int = 1
class ProviderIn(BaseModel):
    base_url: str
    api_key: str | None = None
    model: str
    image_model: str = ""
    timeout_seconds: int = 120
class ExportIn(BaseModel):
    include_answers: bool = True
    black_white: bool = False
class ChatIn(BaseModel):
    content: str = ""

def svc(db=Depends(get_db), user: User = teacher):
    return LessonPlanService(db, user)

@router.get("/projects")
def list_projects(service=Depends(svc)):
    rows = service.db.scalars(select(LessonPlanProject).where(LessonPlanProject.owner_id == service.user.id).order_by(LessonPlanProject.updated_at.desc()))
    return {"items": [service.serialize(p) for p in rows]}

@router.post("/projects", status_code=201)
def create_project(payload: ProjectIn, service=Depends(svc)):
    return service.create(payload.title, payload.request_text, payload.course_id)

@router.get("/projects/{project_id}")
def get_project(project_id: str, service=Depends(svc)):
    return service.serialize(service.project(project_id))

@router.delete("/projects/{project_id}")
def delete_project(project_id: str, service=Depends(svc)):
    p = service.project(project_id); service.db.delete(p); service.db.commit(); return {"ok": True}

@router.post("/projects/{project_id}/generate")
def generate(project_id: str, service=Depends(svc)):
    return service.run(project_id)

@router.post("/projects/{project_id}/requirements/chat")
def requirements_chat(project_id: str, payload: ChatIn, service=Depends(svc)):
    p = service.project(project_id); history = list((p.settings_json or {}).get("chat", []));
    if payload.content.strip(): history.append(payload.content.strip())
    p.settings_json = {**(p.settings_json or {}), "chat": history}; service.db.commit()
    questions = ["这份学案面向哪个年级和学科？", "希望学生完成哪些学习任务（讲解、练习、实验或探究）？", "你希望最终打印成几页，是否需要答案区？"]
    index = min(len(history), len(questions) - 1)
    ready = len(history) >= 3
    return {"message": questions[index] if not ready else "需求已整理完成，可以开始生成学案。", "ready": ready, "history": history}

@router.get("/projects/{project_id}/pages")
def pages(project_id: str, service=Depends(svc)):
    p = service.project(project_id)
    return {"items": [{"id": x.id, "title": x.title, "page_role": x.page_role, "sort_order": x.sort_order, "document": x.document_json, "revision": x.revision, "status": x.status} for x in sorted(p.pages, key=lambda x: x.sort_order)]}

@router.patch("/projects/{project_id}/pages/{page_id}/document")
def patch_document(project_id: str, page_id: str, payload: DocumentIn, service=Depends(svc)):
    from fastapi import HTTPException
    p = service.project(project_id); page = service.db.scalar(select(LessonPlanPage).where(LessonPlanPage.id == page_id, LessonPlanPage.project_id == p.id))
    if not page: raise HTTPException(404, "页面不存在")
    if payload.revision != page.revision: raise HTTPException(409, "页面已被更新，请刷新后重试")
    page.document_json = payload.document; page.revision += 1; page.status = "edited"; service.db.commit()
    return {"id": page.id, "document": page.document_json, "revision": page.revision, "status": page.status}

@router.post("/projects/{project_id}/files", status_code=201)
def upload(project_id: str, file: UploadFile = File(...), service=Depends(svc)):
    p = service.project(project_id); root = settings.ppt_storage_path / "lesson_plans" / p.id / "assets"; root.mkdir(parents=True, exist_ok=True)
    name = Path(file.filename or "asset.bin").name; path = root / name; path.write_bytes(file.file.read())
    asset = LessonPlanAsset(project_id=p.id, source_type="upload", title=name, file_path=str(path), public_url=f"/api/lesson-plans/projects/{p.id}/assets/{name}"); service.db.add(asset); service.db.commit(); service.db.refresh(asset)
    return {"id": asset.id, "title": asset.title, "public_url": asset.public_url, "source_type": asset.source_type}

@router.get("/projects/{project_id}/assets/{filename}")
def asset(project_id: str, filename: str, service=Depends(svc)):
    p = service.project(project_id); return FileResponse(settings.ppt_storage_path / "lesson_plans" / p.id / "assets" / Path(filename).name)

@router.post("/projects/{project_id}/exports", status_code=202)
def export_project(project_id: str, payload: ExportIn, service=Depends(svc)):
    p = service.project(project_id); root = settings.ppt_storage_path / "lesson_plans" / p.id; root.mkdir(parents=True, exist_ok=True)
    job = LessonPlanExportJob(project_id=p.id, status="running"); service.db.add(job); service.db.flush()
    css = "@page{size:A4;margin:0}body{margin:0;font-family:Arial,'Microsoft YaHei',sans-serif}.page{width:210mm;height:297mm;position:relative;page-break-after:always;overflow:hidden;background:#fff}.el{position:absolute;white-space:pre-wrap;overflow:hidden}" + ("*{filter:grayscale(1)}" if payload.black_white else "")
    pages_html = []
    for page in sorted(p.pages, key=lambda x: x.sort_order):
        els = []
        for el in (page.document_json or {}).get("elements", []):
            text = str(el.get("text") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            style = f"left:{el.get('x',0)}%;top:{el.get('y',0)}%;width:{el.get('w',100)}%;height:{el.get('h',10)}%;font-size:{el.get('font_size',16)}px;font-weight:{el.get('font_weight',400)};color:{el.get('color','#163d31')}"
            els.append(f'<div class="el" style="{style}">{text}</div>')
        pages_html.append('<section class="page">' + ''.join(els) + '</section>')
    html = f"<!doctype html><meta charset='utf-8'><style>{css}</style>" + ''.join(pages_html)
    html_path = root / f"lesson-plan-{job.id}.html"; pdf_path = root / f"lesson-plan-{job.id}.pdf"; html_path.write_text(html, encoding="utf-8")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True); page = browser.new_page(); page.set_content(html, wait_until="networkidle"); page.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True); browser.close()
        job.status="completed"; job.html_path=str(html_path); job.pdf_path=str(pdf_path); service.db.add(LessonPlanEvent(project_id=p.id,event_type="export.completed",payload_json={"job_id":job.id})); service.db.commit()
    except Exception as exc:
        job.status="failed"; job.error_message=str(exc); service.db.commit()
    return {"id": job.id, "status": job.status}

@router.get("/projects/{project_id}/exports/{export_id}")
def export_status(project_id: str, export_id: str, service=Depends(svc)):
    p=service.project(project_id); job=service.db.scalar(select(LessonPlanExportJob).where(LessonPlanExportJob.id==export_id, LessonPlanExportJob.project_id==p.id))
    if not job: from fastapi import HTTPException; raise HTTPException(404,"导出任务不存在")
    return {"id":job.id,"status":job.status,"error":job.error_message}

@router.get("/projects/{project_id}/exports/{export_id}/download")
def download_export(project_id: str, export_id: str, service=Depends(svc)):
    p=service.project(project_id); job=service.db.scalar(select(LessonPlanExportJob).where(LessonPlanExportJob.id==export_id, LessonPlanExportJob.project_id==p.id))
    if not job or job.status != "completed": from fastapi import HTTPException; raise HTTPException(409,"导出尚未完成")
    return FileResponse(job.pdf_path, filename="lesson-plan.pdf", media_type="application/pdf")

@router.get("/projects/{project_id}/events/stream")
async def events(project_id: str, last_event_id: int = Query(0), service=Depends(svc)):
    service.project(project_id)
    async def gen():
        current = last_event_id
        for _ in range(120):
            rows = list(service.db.scalars(select(LessonPlanEvent).where(LessonPlanEvent.project_id == project_id, LessonPlanEvent.id > current).order_by(LessonPlanEvent.id)))
            for row in rows:
                current = row.id; yield f"id: {row.id}\ndata: {json.dumps({'id': row.id, 'event_type': row.event_type, 'payload': row.payload_json}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(.5)
    return StreamingResponse(gen(), media_type="text/event-stream")
