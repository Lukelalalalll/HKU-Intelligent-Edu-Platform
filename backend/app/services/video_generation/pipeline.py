from datetime import datetime, timezone
import os
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.models import VideoAsset, VideoGenerationJob, VideoProject, VideoScene, VideoSource

from .base import VideoProviderError
from .coze_provider import CozeProvider
from .local_provider import LocalProvider
from .schemas import VideoGenerationInput


def get_provider(name: str):
    if name == "coze":
        return CozeProvider()
    if name == "local":
        return LocalProvider()
    raise VideoProviderError(f"不支持的视频 provider：{name}")


def run_video_job(job_id: str) -> dict[str, Any]:
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        job = db.get(VideoGenerationJob, job_id)
        if not job:
            raise VideoProviderError("视频任务不存在")
        project = db.get(VideoProject, job.project_id)
        if not project:
            raise VideoProviderError("视频项目不存在")
        provider = get_provider(job.provider)
        if job.status == "canceled":
            return {"status": "canceled"}
        job.attempts = (job.attempts or 0) + 1
        job.status, job.stage, job.progress, job.started_at = "preparing", "准备生成", 5, datetime.now(timezone.utc)
        db.commit()
        config = project.config_json or {}
        source_rows = db.scalars(select(VideoSource).where(VideoSource.project_id == project.id).order_by(VideoSource.created_at)).all()
        source_text = "\n\n".join(item.extracted_text for item in source_rows if item.extracted_text.strip())
        request = VideoGenerationInput(
            project_id=project.id,
            title=project.title,
            course_id=project.course_id,
            source_text="\n\n".join(value for value in (project.input_text, source_text) if value),
            source_material_ids=[item.file_asset_id for item in source_rows if item.file_asset_id],
            language=project.language,
            duration_seconds=project.duration_seconds,
            style=project.style,
            learning_objectives=config.get("learning_objectives", []),
            audience=config.get("audience", ""),
            voice_enabled=config.get("voice_enabled", True),
            captions_enabled=config.get("captions_enabled", True),
            avatar_enabled=config.get("avatar_enabled", False),
        )
        job.status, job.stage, job.progress = "scripting", "生成脚本和分镜", 20
        db.commit()
        output = provider.run_generation(request, job.provider_job_id)
        db.refresh(job)
        if job.status == "canceled":
            provider.cancel_generation(output.provider_job_id or job.provider_job_id or "")
            return {"status": "canceled"}
        job.provider_job_id = output.provider_job_id or job.provider_job_id
        if getattr(provider, "last_request_id", None):
            output.metadata["provider_request_id"] = provider.last_request_id
        job.total_scenes = len(output.scenes)
        job.status, job.stage, job.progress = "generating_visuals", "准备视觉素材", 45
        db.commit()
        for index, scene in enumerate(output.scenes, start=1):
            existing = db.query(VideoScene).filter(VideoScene.project_id == project.id, VideoScene.order_index == index).first()
            if existing is None:
                existing = VideoScene(project_id=project.id, order_index=index)
                db.add(existing)
            existing.title = f"场景 {index}"; existing.duration_seconds = scene.duration_seconds; existing.narration = scene.narration; existing.onscreen_text = scene.onscreen_text; existing.visual_prompt = scene.visual_prompt; existing.status = "ready"
            job.current_scene = index
            job.progress = min(60, 45 + int(index / max(1, len(output.scenes)) * 15))
            db.commit()
        if isinstance(provider, LocalProvider) or (not output.video_url and output.scenes):
            job.status, job.stage, job.progress = "generating_audio", "生成旁白和字幕", 65
            db.commit()
            renderer = provider if isinstance(provider, LocalProvider) else LocalProvider()
            paths = renderer.render(output, job.id)
            job.status, job.stage, job.progress = "rendering", "合成教学视频", 85
            db.commit()
            for kind, path in paths.items():
                if not path: continue
                asset_type = "captions" if kind == "captions" else "srt" if kind == "srt" else "audio" if kind == "audio" else "video" if kind == "video" else "script"
                mime_type = "text/vtt" if kind == "captions" else "application/x-subrip" if kind == "srt" else "audio/wav" if kind == "audio" else "video/mp4" if kind == "video" else "text/plain"
                db.add(VideoAsset(project_id=project.id, job_id=job.id, asset_type=asset_type, storage_key=path, mime_type=mime_type, size_bytes=os.path.getsize(path)))
            output.metadata["local_paths"] = paths
        else:
            job.status, job.stage, job.progress = "rendering", "整理视频产物", 85
            db.commit()
            for asset_type, url, mime_type in (("video", output.video_url, "video/mp4"), ("audio", output.audio_url, "audio/mpeg"), ("captions", output.captions_url, "text/vtt")):
                if url:
                    db.add(VideoAsset(project_id=project.id, job_id=job.id, asset_type=asset_type, storage_key=url, public_url=url, mime_type=mime_type))
        job.result_json = output.model_dump(); job.status, job.stage, job.progress, job.completed_at = "completed", "完成", 100, datetime.now(timezone.utc)
        project.status = "completed"
        db.commit()
        return job.result_json
    except Exception as exc:
        db.rollback()
        job = db.get(VideoGenerationJob, job_id)
        if job:
            job.status = "canceled" if job.status == "canceled" else "failed"; job.error_message = str(exc)[:2000]; job.stage = "失败"; db.commit()
            raw = getattr(exc, "raw_response", None)
            if raw:
                job.result_json = {"raw_provider_response": raw}; db.commit()
        raise
    finally:
        db.close()
