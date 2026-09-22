import hashlib
import json
import secrets
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.core.config import settings
from app.db.session import get_db
from app.jobs.dispatcher import stage_and_publish
from app.models import Course, FileAsset, User, UserRole, VideoAsset, VideoGenerationJob, VideoProject, VideoScene, VideoSource
from app.schemas.video import VideoAssetOut, VideoGenerateIn, VideoJobOut, VideoOut, VideoProjectCreate, VideoProjectPatch, VideoSceneOut, VideoScenePatch, VideoSourceCreate, VideoSourceOut

router = APIRouter(prefix="/api/teacher/video-projects", tags=["teacher-video"])


@router.get("/providers/health")
def provider_health(user: User = Depends(require_roles(UserRole.teacher))):
    from app.services.video_generation import get_provider
    return {name: get_provider(name).health_check() for name in ("coze", "local")}


def project_or_404(db: Session, user: User, project_id: str) -> VideoProject:
    project = db.scalar(select(VideoProject).where(VideoProject.id == project_id, VideoProject.owner_id == user.id).options(selectinload(VideoProject.sources), selectinload(VideoProject.scenes)))
    if not project:
        raise HTTPException(status_code=404, detail="视频项目不存在")
    return project


@router.get("", response_model=list[VideoOut])
def list_projects(user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    return db.scalars(select(VideoProject).where(VideoProject.owner_id == user.id).order_by(VideoProject.updated_at.desc())).all()


@router.post("", response_model=VideoOut, status_code=201)
def create_project(payload: VideoProjectCreate, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    if payload.course_id and not db.scalar(select(Course).where(Course.id == payload.course_id, Course.teacher_id == user.id)):
        raise HTTPException(status_code=404, detail="课程不存在或不属于当前教师")
    config = {"learning_objectives": payload.learning_objectives, "audience": payload.audience, "voice_enabled": payload.voice_enabled, "captions_enabled": payload.captions_enabled, "avatar_enabled": payload.avatar_enabled}
    project = VideoProject(owner_id=user.id, course_id=payload.course_id, title=payload.title.strip(), description=payload.description, provider=payload.provider, language=payload.language, duration_seconds=payload.duration_seconds, style=payload.style, input_text=payload.input_text, config_json=config)
    db.add(project); db.commit(); db.refresh(project)
    return project


@router.get("/{project_id}", response_model=VideoOut)
def get_project(project_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    return project_or_404(db, user, project_id)


@router.patch("/{project_id}", response_model=VideoOut)
def patch_project(project_id: str, payload: VideoProjectPatch, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project = project_or_404(db, user, project_id); values = payload.model_dump(exclude_unset=True); config = dict(project.config_json or {})
    for key in ("learning_objectives", "audience", "voice_enabled", "captions_enabled", "avatar_enabled"):
        if key in values: config[key] = values.pop(key)
    for key, value in values.items(): setattr(project, key, value)
    project.config_json = config; db.commit(); db.refresh(project); return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project = project_or_404(db, user, project_id)
    job_ids = [item.id for item in project.jobs]
    db.delete(project); db.commit()
    for job_id in job_ids:
        shutil.rmtree(settings.video_storage_path / job_id, ignore_errors=True)


@router.post("/{project_id}/sources", response_model=VideoSourceOut, status_code=201)
def add_source(project_id: str, payload: VideoSourceCreate, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project_or_404(db, user, project_id)
    if payload.file_asset_id and not db.scalar(select(FileAsset).where(FileAsset.id == payload.file_asset_id, FileAsset.uploader_id == user.id)):
        raise HTTPException(status_code=404, detail="文件不存在")
    source = VideoSource(project_id=project_id, file_asset_id=payload.file_asset_id, source_type=payload.source_type, title=payload.title, extracted_text=payload.extracted_text, metadata_json=payload.metadata)
    db.add(source); db.commit(); db.refresh(source); return source


@router.post("/{project_id}/generate", response_model=VideoJobOut, status_code=202)
def generate(project_id: str, payload: VideoGenerateIn = VideoGenerateIn(), user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project = project_or_404(db, user, project_id); key = payload.idempotency_key or secrets.token_urlsafe(24)
    existing = db.scalar(select(VideoGenerationJob).where(VideoGenerationJob.owner_id == user.id, VideoGenerationJob.idempotency_key == key))
    if existing: return existing
    job = VideoGenerationJob(project_id=project.id, owner_id=user.id, provider=project.provider, idempotency_key=key, status="queued", stage="排队中")
    project.status = "queued"; db.add(job); db.flush(); task_id = f"video-generation:{job.id}"; job.queue_task_id = task_id; db.commit(); stage_and_publish(db, "video_generation", (job.id,), task_id)
    return job


def enqueue_job(project: VideoProject, user: User, db: Session, *, idempotency_key: str | None = None) -> VideoGenerationJob:
    key = idempotency_key or secrets.token_urlsafe(24)
    existing = db.scalar(select(VideoGenerationJob).where(VideoGenerationJob.owner_id == user.id, VideoGenerationJob.idempotency_key == key))
    if existing:
        return existing
    job = VideoGenerationJob(project_id=project.id, owner_id=user.id, provider=project.provider, idempotency_key=key, status="queued", stage="排队中")
    project.status = "queued"; db.add(job); db.flush(); task_id = f"video-generation:{job.id}"; job.queue_task_id = task_id; db.commit(); stage_and_publish(db, "video_generation", (job.id,), task_id)
    return job


def get_job(db: Session, user: User, project_id: str, job_id: str) -> VideoGenerationJob:
    project_or_404(db, user, project_id)
    item = db.scalar(select(VideoGenerationJob).where(VideoGenerationJob.id == job_id, VideoGenerationJob.project_id == project_id, VideoGenerationJob.owner_id == user.id))
    if not item: raise HTTPException(status_code=404, detail="任务不存在")
    return item


@router.get("/{project_id}/jobs", response_model=list[VideoJobOut])
def jobs(project_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project_or_404(db, user, project_id); return db.scalars(select(VideoGenerationJob).where(VideoGenerationJob.project_id == project_id, VideoGenerationJob.owner_id == user.id).order_by(VideoGenerationJob.created_at.desc())).all()


@router.get("/{project_id}/jobs/{job_id}", response_model=VideoJobOut)
def job(project_id: str, job_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)): return get_job(db, user, project_id, job_id)


@router.post("/{project_id}/jobs/{job_id}/cancel", response_model=VideoJobOut)
def cancel_job(project_id: str, job_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    item = get_job(db, user, project_id, job_id)
    if item.provider_job_id:
        try:
            from app.services.video_generation import get_provider
            get_provider(item.provider).cancel_generation(item.provider_job_id)
        except Exception:
            # Persist cancellation even if a remote provider is temporarily
            # unavailable; the worker observes this durable state.
            pass
    item.status = "canceled"; item.stage = "已取消"; item.error_message = None; db.commit(); return item


@router.post("/{project_id}/jobs/{job_id}/retry", response_model=VideoJobOut, status_code=202)
def retry_job(project_id: str, job_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    old = get_job(db, user, project_id, job_id); project = project_or_404(db, user, project_id); item = VideoGenerationJob(project_id=project_id, owner_id=user.id, provider=project.provider, idempotency_key=f"{old.idempotency_key}:retry:{old.attempts + 1}", status="queued", stage="排队中")
    db.add(item); db.flush(); task_id = f"video-generation:{item.id}"; item.queue_task_id = task_id; db.commit(); stage_and_publish(db, "video_generation", (item.id,), task_id); return item


@router.get("/{project_id}/scenes", response_model=list[VideoSceneOut])
def scenes(project_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project_or_404(db, user, project_id); return db.scalars(select(VideoScene).where(VideoScene.project_id == project_id).order_by(VideoScene.order_index)).all()


@router.get("/{project_id}/sources", response_model=list[VideoSourceOut])
def sources(project_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project_or_404(db, user, project_id)
    return db.scalars(select(VideoSource).where(VideoSource.project_id == project_id).order_by(VideoSource.created_at)).all()


@router.patch("/{project_id}/scenes/{scene_id}", response_model=VideoSceneOut)
def patch_scene(project_id: str, scene_id: str, payload: VideoScenePatch, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project_or_404(db, user, project_id); scene = db.scalar(select(VideoScene).where(VideoScene.id == scene_id, VideoScene.project_id == project_id))
    if not scene: raise HTTPException(status_code=404, detail="场景不存在")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(scene, key, value)
    db.commit(); db.refresh(scene); return scene


@router.post("/{project_id}/scenes/{scene_id}/generate", response_model=VideoJobOut, status_code=202)
def generate_scene(project_id: str, scene_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project = project_or_404(db, user, project_id)
    scene = db.scalar(select(VideoScene).where(VideoScene.id == scene_id, VideoScene.project_id == project_id))
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")
    project.config_json = {**(project.config_json or {}), "regenerate_scene_id": scene.id}
    db.commit()
    return enqueue_job(project, user, db, idempotency_key=f"scene:{scene.id}:{time.time_ns()}")


@router.get("/{project_id}/events/stream")
def stream_events(project_id: str, request: Request, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project_or_404(db, user, project_id)
    def events():
        from app.db.session import SessionLocal
        local = SessionLocal()
        try:
            sent: set[str] = set()
            deadline = time.monotonic() + 900
            while time.monotonic() < deadline:
                items = local.scalars(select(VideoGenerationJob).where(VideoGenerationJob.project_id == project_id, VideoGenerationJob.owner_id == user.id).order_by(VideoGenerationJob.created_at.desc())).all()
                terminal = True
                for item in items:
                    payload = {"type": "error", "job_id": item.id, "detail": item.error_message} if item.error_message else {"type": "status", "job_id": item.id, "status": item.status, "stage": item.stage, "progress": item.progress, "current_scene": item.current_scene, "total_scenes": item.total_scenes}
                    fingerprint = json.dumps(payload, sort_keys=True, ensure_ascii=False)
                    if fingerprint not in sent:
                        sent.add(fingerprint); yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    if item.status not in {"completed", "failed", "canceled"}: terminal = False
                local.expire_all()
                if items and terminal: break
                time.sleep(0.5)
        finally: local.close()
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/{project_id}/assets/{asset_id}/download")
def download_asset(project_id: str, asset_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project_or_404(db, user, project_id); asset = db.scalar(select(VideoAsset).where(VideoAsset.id == asset_id, VideoAsset.project_id == project_id))
    if not asset: raise HTTPException(status_code=404, detail="视频产物不存在")
    path = Path(asset.storage_key)
    if asset.public_url and str(asset.storage_key).startswith(("https://", "http://")):
        return RedirectResponse(asset.public_url)
    if not path.is_file(): raise HTTPException(status_code=404, detail="视频产物尚未生成")
    return FileResponse(path, media_type=asset.mime_type, filename=path.name)


@router.get("/{project_id}/assets", response_model=list[VideoAssetOut])
def assets(project_id: str, user: User = Depends(require_roles(UserRole.teacher)), db: Session = Depends(get_db)):
    project_or_404(db, user, project_id)
    return db.scalars(select(VideoAsset).where(VideoAsset.project_id == project_id).order_by(VideoAsset.created_at.desc())).all()


@router.post("/webhooks/coze")
async def coze_webhook(request: Request):
    if not settings.coze_webhook_secret: raise HTTPException(status_code=404, detail="Coze webhook 未启用")
    signature = request.headers.get("X-Coze-Signature", ""); expected = hashlib.sha256(settings.coze_webhook_secret.encode()).hexdigest()
    if not secrets.compare_digest(signature, expected): raise HTTPException(status_code=401, detail="Invalid webhook signature")
    return {"accepted": True}


webhook_router = APIRouter(prefix="/api/teacher/video", tags=["teacher-video"])
webhook_router.add_api_route("/webhooks/coze", coze_webhook, methods=["POST"])
