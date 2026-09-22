from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class VideoProjectCreate(BaseModel):
    title: str = Field(default="未命名教学视频", min_length=1, max_length=200)
    course_id: str | None = None
    description: str = Field(default="", max_length=10000)
    input_text: str = Field(default="", max_length=100000)
    learning_objectives: list[str] = Field(default_factory=list, max_length=20)
    audience: str = Field(default="", max_length=500)
    language: str = Field(default="zh-HK", max_length=30)
    duration_seconds: int = Field(default=120, ge=15, le=900)
    style: str = Field(default="lecture", max_length=60)
    voice_enabled: bool = True
    captions_enabled: bool = True
    avatar_enabled: bool = False
    provider: Literal["coze", "local"] = "coze"


class VideoProjectPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    input_text: str | None = Field(default=None, max_length=100000)
    provider: Literal["coze", "local"] | None = None
    duration_seconds: int | None = Field(default=None, ge=15, le=900)
    style: str | None = Field(default=None, max_length=60)
    language: str | None = Field(default=None, max_length=30)
    learning_objectives: list[str] | None = None
    audience: str | None = None
    voice_enabled: bool | None = None
    captions_enabled: bool | None = None
    avatar_enabled: bool | None = None


class VideoSourceCreate(BaseModel):
    file_asset_id: str | None = None
    source_type: str = Field(default="text", max_length=30)
    title: str = Field(default="讲稿", max_length=255)
    extracted_text: str = Field(default="", max_length=100000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VideoGenerateIn(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=255)


class VideoScenePatch(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    narration: str | None = Field(default=None, max_length=50000)
    onscreen_text: str | None = Field(default=None, max_length=10000)
    visual_prompt: str | None = Field(default=None, max_length=10000)
    duration_seconds: int | None = Field(default=None, ge=1, le=900)


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; owner_id: str; course_id: str | None; title: str; description: str; provider: str; status: str; language: str; duration_seconds: int; style: str; input_text: str; config_json: dict; created_at: datetime; updated_at: datetime


class VideoSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; project_id: str; file_asset_id: str | None; source_type: str; title: str; extracted_text: str; metadata_json: dict; created_at: datetime


class VideoSceneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; project_id: str; order_index: int; title: str; narration: str; onscreen_text: str; visual_prompt: str; duration_seconds: int; status: str; metadata_json: dict


class VideoJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; project_id: str; owner_id: str; provider: str; provider_job_id: str | None; status: str; stage: str; progress: int; current_scene: int; total_scenes: int; result_json: dict; error_message: str | None; idempotency_key: str; created_at: datetime; started_at: datetime | None; completed_at: datetime | None


class VideoAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; project_id: str; job_id: str; asset_type: str; storage_key: str; public_url: str | None; mime_type: str; size_bytes: int; metadata_json: dict; created_at: datetime
