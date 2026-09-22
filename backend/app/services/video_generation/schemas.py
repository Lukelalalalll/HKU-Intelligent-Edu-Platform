from typing import Any, Literal

from pydantic import BaseModel, Field


VideoStatus = Literal["queued", "preparing", "scripting", "generating_audio", "generating_visuals", "rendering", "completed", "failed", "canceled"]


class VideoGenerationInput(BaseModel):
    project_id: str
    title: str
    course_id: str | None = None
    source_text: str = ""
    source_material_ids: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    audience: str = ""
    language: str = "zh-HK"
    duration_seconds: int = Field(default=120, ge=15, le=900)
    style: str = "lecture"
    voice_enabled: bool = True
    captions_enabled: bool = True
    avatar_enabled: bool = False
    output_format: str = "mp4"


class VideoSceneData(BaseModel):
    id: str | None = None
    order: int = 0
    duration_seconds: int = 15
    narration: str = ""
    onscreen_text: str = ""
    visual_prompt: str = ""
    asset_urls: list[str] = Field(default_factory=list)
    caption_text: str = ""


class VideoGenerationOutput(BaseModel):
    script: str = ""
    scenes: list[VideoSceneData] = Field(default_factory=list)
    audio_url: str | None = None
    video_url: str | None = None
    captions_url: str | None = None
    render_mode: str | None = None
    provider_job_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VideoProgress(BaseModel):
    status: VideoStatus = "queued"
    progress: int = Field(default=0, ge=0, le=100)
    stage: str = "queued"
    current_scene: int = 0
    total_scenes: int = 0
    error_message: str | None = None
    provider_job_id: str | None = None


def normalize_output(value: Any) -> VideoGenerationOutput:
    if isinstance(value, VideoGenerationOutput):
        return value
    if not isinstance(value, dict):
        raise ValueError("视频 provider 返回值必须是 JSON 对象")
    scenes = value.get("scenes") or []
    normalized: list[dict[str, Any]] = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"场景 {index} 不是 JSON 对象")
        normalized.append({
            "id": scene.get("id"),
            "order": scene.get("order", scene.get("order_index", index)),
            "duration_seconds": scene.get("duration_seconds", scene.get("duration", 15)),
            "narration": scene.get("narration", scene.get("voiceover", "")),
            "onscreen_text": scene.get("onscreen_text", scene.get("on_screen_text", "")),
            "visual_prompt": scene.get("visual_prompt", ""),
            "asset_urls": scene.get("asset_urls", scene.get("assets", [])) or [],
            "caption_text": scene.get("caption_text", scene.get("narration", "")),
        })
    return VideoGenerationOutput(
        script=value.get("script", value.get("text", "")) or "",
        scenes=normalized,
        audio_url=value.get("audio_url"),
        video_url=value.get("video_url"),
        captions_url=value.get("captions_url", value.get("subtitle_url")),
        render_mode=value.get("render_mode"),
        provider_job_id=value.get("provider_job_id", value.get("run_id")),
        metadata=value.get("metadata", {}) or {},
    )
