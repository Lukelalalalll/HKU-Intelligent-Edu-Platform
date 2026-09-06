import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, File, Header, Query, UploadFile, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models import PptAgentEvent, PptExportJob, PptPage, PptProject, PptProviderConfig, PptGenerationJob, User, UserRole
from app.schemas.ppt import ActionIn, BatchIn, ExportIn, MessageIn, OutlineGenerateIn, PagePatchIn, ProjectCreateIn, ProjectPatchIn, ProviderConfigIn, RequirementPatchIn, RequirementChatIn, DocumentPatchIn, StoryboardPatchIn, CheckpointConfirmIn, ThemeSelectIn, LayoutAssignmentsIn, VisualSelectionIn
from app.services.ppt_agent import PptAgentService, decrypt_api_key, encrypt_api_key
from app.services.ppt_edit_agent import PptEditAgent
from app.services.ppt_theme import get_theme, list_layouts, list_themes, render_slide_svg

router = APIRouter(prefix="/api/ppt", tags=["ppt-agent"])
teacher = Depends(require_roles(UserRole.teacher))
export_executor = ThreadPoolExecutor(max_workers=2)


def svc(db: Session = Depends(get_db), user: User = teacher) -> PptAgentService:
    return PptAgentService(db, user)


@router.get("/settings/provider")
def get_provider(user: User = teacher, db: Session = Depends(get_db)):
    c = db.scalar(select(PptProviderConfig).where(PptProviderConfig.user_id == user.id))
    key = decrypt_api_key(c.api_key_encrypted) if c else settings.llm_api_key
    return {"base_url": c.base_url if c else settings.llm_base_url, "api_key_configured": bool(key), "api_key_masked": (key[:4] + "••••" + key[-4:]) if len(key) > 8 else ("••••••••" if key else ""), "model": c.model if c else settings.llm_model, "embedding_model": c.embedding_model if c else settings.embedding_model, "timeout_seconds": c.timeout_seconds if c else 120}


@router.patch("/settings/provider")
def patch_provider(payload: ProviderConfigIn, user: User = teacher, db: Session = Depends(get_db)):
    c = db.scalar(select(PptProviderConfig).where(PptProviderConfig.user_id == user.id))
    if not c: c = PptProviderConfig(user_id=user.id); db.add(c)
    c.base_url, c.model, c.embedding_model, c.timeout_seconds = payload.base_url.rstrip("/"), payload.model, payload.embedding_model, payload.timeout_seconds
    if payload.api_key: c.api_key_encrypted = encrypt_api_key(payload.api_key)
    db.commit(); return {"message": "模型配置已保存"}


@router.post("/settings/provider/test")
def test_provider(user: User = teacher, db: Session = Depends(get_db)):
    from app.services.ppt_agent import ProviderGateway
    ProviderGateway(db, user.id).json("只输出 JSON：{ok:true}", {"ping": "pong"})
    return {"ok": True}


@router.delete("/settings/provider")
def clear_provider(user: User = teacher, db: Session = Depends(get_db)):
    c = db.scalar(select(PptProviderConfig).where(PptProviderConfig.user_id == user.id))
    if c: db.delete(c); db.commit()
    return {"message": "模型配置已清除"}


@router.get("/projects")
def list_projects(service: PptAgentService = Depends(svc)): return {"items": service.list_projects()}

@router.get("/themes")
def themes(): return {"items": list_themes()}

@router.get("/themes/{theme_id}/layouts")
def theme_layouts(theme_id: str): return {"items": list_layouts(theme_id)}

@router.get("/themes/{theme_id}/layouts/{layout_id}/preview.svg")
def theme_layout_preview(theme_id: str, layout_id: str):
    from types import SimpleNamespace
    layouts = {item["id"]: item for item in list_layouts(theme_id)}
    layout = layouts.get(layout_id)
    if not layout:
        from fastapi import HTTPException
        raise HTTPException(404, "布局不存在")
    page = SimpleNamespace(title="主题预览", section_title="PPT Studio", bullets_json=["教学重点示例", "清晰的内容层级", "适合课堂投影阅读"])
    return Response(content=render_slide_svg(page, get_theme(theme_id), layout), media_type="image/svg+xml")


@router.post("/projects", status_code=201)
def create_project(payload: ProjectCreateIn, service: PptAgentService = Depends(svc)): return service.create_project(payload.title, payload.request_text, payload.course_id)


@router.get("/projects/{project_id}")
def get_project(project_id: str, service: PptAgentService = Depends(svc)): return service.serialize_project(service.project(project_id))


@router.patch("/projects/{project_id}")
def patch_project(project_id: str, payload: ProjectPatchIn, service: PptAgentService = Depends(svc)):
    p = service.project(project_id)
    if payload.title is not None: p.title = payload.title.strip() or p.title
    if payload.request_text is not None: p.request_text = payload.request_text.strip()
    service.db.commit(); return service.serialize_project(p)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, service: PptAgentService = Depends(svc)):
    service.delete_project(project_id); return {"message": "项目已删除"}


@router.get("/projects/{project_id}/requirements")
def get_requirements(project_id: str, service: PptAgentService = Depends(svc)): return service.requirements(project_id)


@router.post("/projects/{project_id}/requirements/chat")
def requirement_chat(project_id: str, payload: RequirementChatIn, service: PptAgentService = Depends(svc)):
    return service.requirement_chat(project_id, payload.content, payload.option_id, payload.option_label, payload.bootstrap)


@router.post("/projects/{project_id}/requirements/chat/stream")
def requirement_chat_stream(project_id: str, payload: RequirementChatIn, service: PptAgentService = Depends(svc)):
    """SSE wrapper for the requirements interview with a streamed assistant reveal."""
    service.project(project_id)

    def event_stream():
        try:
            yield f"data: {json.dumps({'type': 'status', 'status': '正在理解你的需求'}, ensure_ascii=False)}\n\n"
            for event in service.requirement_chat_stream(project_id, payload.content, payload.option_id, payload.option_label, payload.bootstrap):
                if event.get("type") == "chunk":
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                elif event.get("type") == "complete":
                    result = event["result"]
                    text = result["message"]["content_md"]
                    yield f"data: {json.dumps({'type': 'complete', 'chat': {'response': text, 'message_id': result['message']['id']}, 'requirement': result}, ensure_ascii=False)}\n\n"
        except HTTPException as exc:
            service.db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'detail': exc.detail}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            service.db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.patch("/projects/{project_id}/requirements")
def patch_requirements(project_id: str, payload: RequirementPatchIn, service: PptAgentService = Depends(svc)): return service.patch_requirements(project_id, payload.model_dump())


@router.post("/projects/{project_id}/requirements:generate")
def generate_requirements(project_id: str, service: PptAgentService = Depends(svc)): return service.generate_requirements(project_id)


@router.post("/projects/{project_id}/outline:generate")
def generate_outline(project_id: str, payload: OutlineGenerateIn, service: PptAgentService = Depends(svc)): return service.generate_outline(project_id, payload.page_count_target)

@router.post("/projects/{project_id}/theme")
def select_theme(project_id: str, payload: ThemeSelectIn, service: PptAgentService = Depends(svc)): return service.select_theme(project_id, payload.theme_id)

@router.put("/projects/{project_id}/layouts")
def assign_layouts(project_id: str, payload: LayoutAssignmentsIn, service: PptAgentService = Depends(svc)): return service.assign_layouts(project_id, payload.assignments, payload.mode)

@router.post("/projects/{project_id}/design:generate")
def generate_design(project_id: str, service: PptAgentService = Depends(svc)):
    return service.start_generation(project_id)


@router.get("/projects/{project_id}/generation-jobs/{job_id}")
def generation_job(project_id: str, job_id: str, service: PptAgentService = Depends(svc)):
    return service.generation_job(project_id, job_id)


@router.post("/projects/{project_id}/generation-jobs/{job_id}:cancel")
def cancel_generation(project_id: str, job_id: str, service: PptAgentService = Depends(svc)):
    return service.cancel_generation(project_id, job_id)


@router.post("/projects/{project_id}/generation-jobs/{job_id}:retry")
def retry_generation(project_id: str, job_id: str, service: PptAgentService = Depends(svc)):
    service.cancel_generation(project_id, job_id)
    return service.start_generation(project_id)


@router.get("/projects/{project_id}/pages")
def list_pages(project_id: str, service: PptAgentService = Depends(svc)):
    p = service.project(project_id); return {"items": [service.serialize_page(x) for x in sorted(p.pages, key=lambda x: x.sort_order)]}


@router.get("/projects/{project_id}/pages/{page_id}")
def get_page(project_id: str, page_id: str, service: PptAgentService = Depends(svc)): return service.serialize_page(service.page(project_id, page_id))


@router.put("/projects/{project_id}/pages/{page_id}/visual-selection")
def save_visual_selection(project_id: str, page_id: str, payload: VisualSelectionIn, service: PptAgentService = Depends(svc)):
    return service.save_visual_selection(project_id, page_id, payload.asset_ids)

@router.get("/projects/{project_id}/pages/{page_id}/preview.svg")
def preview_page(project_id: str, page_id: str, layout_id: str | None = Query(default=None), service: PptAgentService = Depends(svc)):
    return Response(content=service.preview_svg(project_id, page_id, layout_id), media_type="image/svg+xml")


@router.get("/projects/{project_id}/assets/{filename}")
def page_asset(project_id: str, filename: str, service: PptAgentService = Depends(svc)):
    """Serve downloaded visual research assets through the same auth boundary."""
    service.project(project_id)
    safe_name = __import__("pathlib").Path(filename).name
    path = settings.ppt_storage_path / project_id / "assets" / safe_name
    if not path.is_file():
        raise HTTPException(404, "素材不存在")
    return FileResponse(path, media_type=None, filename=safe_name)


@router.patch("/projects/{project_id}/pages/{page_id}")
def patch_page(project_id: str, page_id: str, payload: PagePatchIn, service: PptAgentService = Depends(svc)): return service.patch_page(project_id, page_id, payload.model_dump())


@router.post("/projects/{project_id}/pages/{page_id}/actions")
def page_action(project_id: str, page_id: str, payload: ActionIn, service: PptAgentService = Depends(svc)): return service.run_action(project_id, page_id, payload.action_type, payload.replace_existing)


@router.post("/projects/{project_id}/actions/batch")
def batch_action(project_id: str, payload: BatchIn, service: PptAgentService = Depends(svc)): return service.run_action(project_id, None, payload.action_type)

@router.get("/projects/{project_id}/visual-jobs/{job_id}")
def visual_job(project_id: str, job_id: str, service: PptAgentService = Depends(svc)):
    return service.generation_job(project_id, job_id)

@router.post("/projects/{project_id}/visual-jobs/{job_id}:cancel")
def cancel_visual_job(project_id: str, job_id: str, service: PptAgentService = Depends(svc)):
    return service.cancel_generation(project_id, job_id)


@router.post("/projects/{project_id}/files", status_code=201)
def upload_file(project_id: str, page_id: str | None = Query(default=None), file: UploadFile = File(...), service: PptAgentService = Depends(svc)): return service.upload_document(project_id, page_id, file)


@router.post("/projects/{project_id}/messages")
def message(project_id: str, payload: MessageIn, service: PptAgentService = Depends(svc)):
    return service.route_message(project_id, payload.content, payload.page_id, payload.option_id, payload.option_label)


@router.post("/projects/{project_id}/messages/stream")
def message_stream(project_id: str, payload: MessageIn, service: PptAgentService = Depends(svc)):
    """Stream the tool-driven preview/editor assistant.

    The API key is resolved inside ``ProviderGateway`` from the logged-in
    teacher's encrypted provider configuration; it is never accepted from the
    browser.
    """
    project = service.project(project_id)
    user_message = service._message(project, "user", payload.content, payload.page_id, {"ui_surface": payload.ui_surface})
    service.db.commit()
    history_rows = service.list_messages(project_id, payload.page_id)
    history = [{"role": row["role"], "content": row["content_md"]} for row in history_rows[:-1] if row["role"] in {"user", "assistant"}][-20:]
    agent = PptEditAgent(service)

    def event_stream():
        assistant_text: list[str] = []
        tool_names: list[str] = []
        try:
            yield f"data: {json.dumps({'type': 'status', 'status': 'Reading deck context'}, ensure_ascii=False)}\n\n"
            for event in agent.run(project_id, payload.page_id, payload.content, history):
                if event.get("type") == "chunk":
                    chunk = str(event.get("chunk") or "")
                    assistant_text.append(chunk)
                elif event.get("type") == "trace":
                    trace = event.get("trace") or {}
                    if trace.get("tool") and trace["tool"] not in tool_names:
                        tool_names.append(trace["tool"])
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            final_text = "".join(assistant_text) or "已完成处理。"
            assistant = service._message(project, "assistant", final_text, payload.page_id, {"tool_calls": tool_names})
            service.db.commit()
            yield f"data: {json.dumps({'type': 'complete', 'chat': {'response': final_text, 'tool_calls': tool_names, 'message_id': assistant.id}}, ensure_ascii=False)}\n\n"
        except HTTPException as exc:
            service.db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'detail': exc.detail}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            service.db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/projects/{project_id}/messages")
def list_messages(project_id: str, page_id: str | None = Query(default=None), service: PptAgentService = Depends(svc)):
    return {"items": service.list_messages(project_id, page_id)}


@router.get("/projects/{project_id}/sources")
def list_sources(project_id: str, service: PptAgentService = Depends(svc)):
    return {"items": service.list_sources(project_id)}

@router.get("/projects/{project_id}/checkpoints")
def list_checkpoints(project_id: str, service: PptAgentService = Depends(svc)):
    return {"items": service.list_checkpoints(project_id)}


@router.post("/projects/{project_id}/checkpoints/{checkpoint_code}:confirm")
def confirm_checkpoint(project_id: str, checkpoint_code: str, payload: CheckpointConfirmIn, service: PptAgentService = Depends(svc)):
    return service.confirm_checkpoint(project_id, checkpoint_code, payload.note)


@router.patch("/projects/{project_id}/pages/{page_id}/document")
def patch_document(project_id: str, page_id: str, payload: DocumentPatchIn, service: PptAgentService = Depends(svc)):
    return service.patch_document(project_id, page_id, payload.document, payload.revision)

@router.post("/projects/{project_id}/pages/{page_id}/document:{direction}")
def restore_document(project_id: str, page_id: str, direction: str, payload: DocumentPatchIn, service: PptAgentService = Depends(svc)):
    if direction not in {"undo", "redo"}:
        from fastapi import HTTPException
        raise HTTPException(400, "仅支持 undo 或 redo")
    return service.restore_document(project_id, page_id, payload.revision, direction)


@router.patch("/projects/{project_id}/storyboard")
def patch_storyboard(project_id: str, payload: StoryboardPatchIn, service: PptAgentService = Depends(svc)):
    p = service.project(project_id)
    pages = {page.id: page for page in p.pages}
    if set(payload.page_ids) != set(pages):
        from fastapi import HTTPException
        raise HTTPException(400, "页面列表必须包含项目内全部页面")
    for index, page_id in enumerate(payload.page_ids):
        pages[page_id].sort_order = index
    service.db.commit()
    return {"items": [service.serialize_page(pages[page_id]) for page_id in payload.page_ids]}


@router.get("/projects/{project_id}/events/stream")
async def stream_events(project_id: str, request_id: str | None = Query(default=None), last_event_id: str | None = Header(default=None, alias="Last-Event-ID"), service: PptAgentService = Depends(svc)):
    service.project(project_id); current = int(last_event_id or 0) if (last_event_id or "0").isdigit() else 0
    async def gen():
        nonlocal current
        for _ in range(1200):
            rows = list(service.db.scalars(select(PptAgentEvent).where(PptAgentEvent.project_id == project_id, PptAgentEvent.id > current).order_by(PptAgentEvent.id.asc()).limit(100)))
            for row in rows:
                current = row.id; yield f"id: {row.id}\ndata: {json.dumps({'id': row.id, 'event_type': row.event_type, 'payload': row.payload_json, 'created_at': row.created_at.isoformat()}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.5)
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _run_export_job(export_id: str, project_id: str, filename: str | None) -> None:
    from app.db.session import SessionLocal
    from app.services.ppt_export import export_project_pptx
    db = SessionLocal()
    try:
        job, project = db.get(PptExportJob, export_id), db.get(PptProject, project_id)
        if not job or not project: return
        job.status = "running"; db.add(PptAgentEvent(project_id=project_id, event_type="export.started", payload_json={"job_id": export_id})); db.commit()
        path = settings.ppt_storage_path / f"{project.id}-{export_id}.pptx"
        export_project_pptx(project, path, filename)
        job.status, job.file_path = "completed", str(path); project.current_stage = "export"; db.add(PptAgentEvent(project_id=project_id, event_type="export.completed", payload_json={"job_id": export_id})); db.commit()
    except Exception as exc:
        db.rollback(); job = db.get(PptExportJob, export_id)
        if job:
            job.status, job.error_message = "failed", str(exc); db.add(PptAgentEvent(project_id=project_id, event_type="export.failed", payload_json={"job_id": export_id, "error": str(exc)})); db.commit()
    finally:
        db.close()


@router.post("/projects/{project_id}/exports", status_code=202)
def export_project(project_id: str, payload: ExportIn, service: PptAgentService = Depends(svc)):
    p = service.project(project_id)
    active = service.db.scalar(select(PptExportJob).where(PptExportJob.project_id == p.id, PptExportJob.status.in_(["queued", "running"])).order_by(PptExportJob.created_at.desc()))
    if active: return {"id": active.id, "status": active.status}
    job = PptExportJob(project_id=p.id, status="queued"); service.db.add(job); service.db.commit(); service.db.refresh(job)
    export_executor.submit(_run_export_job, job.id, p.id, payload.filename)
    return {"id": job.id, "status": job.status}


@router.get("/projects/{project_id}/exports/{export_id}/download")
def download_export(project_id: str, export_id: str, service: PptAgentService = Depends(svc)):
    service.project(project_id); job = service.db.scalar(select(PptExportJob).where(PptExportJob.id == export_id, PptExportJob.project_id == project_id))
    if not job: raise HTTPException(404, "导出任务不存在")
    if job.status != "completed" or not job.file_path: raise HTTPException(409, {"status": job.status, "error": job.error_message or "导出尚未完成"})
    return FileResponse(job.file_path, filename="courseware.pptx", media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")


@router.get("/projects/{project_id}/exports/{export_id}")
def export_status(project_id: str, export_id: str, service: PptAgentService = Depends(svc)):
    service.project(project_id)
    job = service.db.scalar(select(PptExportJob).where(PptExportJob.id == export_id, PptExportJob.project_id == project_id))
    if not job: raise HTTPException(404, "导出任务不存在")
    return {"id": job.id, "status": job.status, "error": job.error_message}
