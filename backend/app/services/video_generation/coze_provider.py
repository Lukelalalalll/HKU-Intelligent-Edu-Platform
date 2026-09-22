import json
import time
from typing import Any

import httpx

from app.core.config import settings

from .base import VideoProvider, VideoProviderError
from .schemas import VideoGenerationInput, VideoGenerationOutput, VideoProgress, normalize_output


class CozeProvider(VideoProvider):
    name = "coze"

    def __init__(self, config=settings, client: httpx.Client | None = None):
        self.config = config
        self._client = client
        self._coze = None
        self.last_request_id: str | None = None

    @property
    def coze(self):
        """Build the official SDK client lazily so API imports stay optional."""
        if self._coze is None:
            try:
                from cozepy import Coze, TokenAuth
            except ImportError as exc:  # pragma: no cover - dependency install choice
                raise VideoProviderError("Coze SDK 未安装，请安装 cozepy") from exc
            self._coze = Coze(auth=TokenAuth(token=self.config.coze_api_token), base_url=self.config.coze_api_base_url)
        return self._coze

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self.config.coze_api_base_url, timeout=self.config.coze_timeout_seconds)
        return self._client

    def validate_config(self) -> None:
        if not self.config.coze_enabled:
            raise VideoProviderError("Coze provider 未启用")
        if not self.config.coze_api_token:
            raise VideoProviderError("Coze API token 尚未配置")
        if not self.config.coze_workflow_id:
            raise VideoProviderError("Coze workflow id 尚未配置")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.config.coze_api_token}", "Content-Type": "application/json"}

    def _payload(self, request: VideoGenerationInput) -> dict[str, Any]:
        return {"workflow_id": self.config.coze_workflow_id, "parameters": {
            "title": request.title, "course_id": request.course_id, "learning_objectives": request.learning_objectives,
            "audience": request.audience, "language": request.language, "duration_seconds": request.duration_seconds,
            "style": request.style, "source_text": request.source_text,
            "source_materials": [{"id": item} for item in request.source_material_ids],
            "need_voice": request.voice_enabled, "need_captions": request.captions_enabled, "need_avatar": request.avatar_enabled,
        }}

    def create_generation_job(self, request: VideoGenerationInput) -> str | None:
        self.validate_config()
        try:
            run = self.coze.workflows.runs.create(
                workflow_id=self.config.coze_workflow_id,
                parameters=self._payload(request)["parameters"],
                bot_id=self.config.coze_bot_id or None,
                is_async=True,
            )
            return str(getattr(run, "execute_id", "") or "") or None
        except Exception:
            # Keep the small HTTP adapter for deployments whose SDK version does
            # not expose the async workflow endpoint yet.
            pass
        response = self.client.post("/v1/workflow/run", headers=self._headers(), json=self._payload(request))
        self.last_request_id = response.headers.get("x-request-id") or response.headers.get("x-log-id")
        if response.status_code >= 400:
            raise VideoProviderError(f"Coze workflow 请求失败（HTTP {response.status_code}）")
        body = response.json()
        return str(body.get("workflow_run_id") or body.get("run_id") or body.get("id") or "") or None

    @staticmethod
    def parse_json_content(content: Any) -> dict[str, Any]:
        if isinstance(content, dict):
            return content
        if isinstance(content, (bytes, bytearray)):
            content = content.decode("utf-8", errors="replace")
        if not isinstance(content, str):
            raise ValueError("Coze 返回内容不是 JSON 文本")
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Coze 返回内容无法解析为 JSON：{exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError("Coze 返回 JSON 顶层必须是对象")
        return value

    def normalize_event(self, event: Any) -> dict[str, Any]:
        if isinstance(event, str):
            event = {"event": event}
        if not isinstance(event, dict):
            return {"type": "error", "detail": "Coze 事件格式无效"}
        event_type = str(event.get("event", event.get("type", ""))).upper()
        if event_type in {"MESSAGE", "CHUNK", "DELTA"}:
            content = event.get("content", event.get("data", ""))
            return {"type": "message", "content": content, "raw": event}
        if event_type in {"ERROR", "FAILED"}:
            return {"type": "error", "detail": str(event.get("message", event.get("error", "Coze workflow failed"))), "raw": event}
        if event_type == "INTERRUPT":
            return {"type": "interrupt", "detail": str(event.get("message", "Coze workflow interrupted")), "raw": event}
        if event_type in {"DONE", "COMPLETED", "SUCCESS"}:
            return {"type": "complete", "raw": event}
        return {"type": "status", "status": str(event.get("status", "preparing")), "raw": event}

    def stream_generation(self, request: VideoGenerationInput):
        """Consume the official workflow SSE stream and normalize its events."""
        self.validate_config()
        try:
            stream = self.coze.workflows.runs.stream(
                workflow_id=self.config.coze_workflow_id,
                parameters=self._payload(request)["parameters"],
                bot_id=self.config.coze_bot_id or None,
            )
            chunks: list[str] = []
            for event in stream:
                event_name = getattr(getattr(event, "event", None), "value", getattr(event, "event", ""))
                event_name = str(event_name).upper()
                if event_name == "MESSAGE":
                    content = str(getattr(getattr(event, "message", None), "content", ""))
                    chunks.append(content)
                    yield {"type": "message", "content": content}
                elif event_name == "ERROR":
                    detail = str(getattr(getattr(event, "error", None), "error_message", "Coze workflow failed"))
                    yield {"type": "error", "detail": detail}
                    return
                elif event_name == "INTERRUPT":
                    yield {"type": "interrupt", "detail": "Coze workflow interrupted"}
                    return
                elif event_name == "DONE":
                    break
            raw = "".join(chunks)
            try:
                output = normalize_output(self.parse_json_content(raw))
            except ValueError as exc:
                yield {"type": "error", "detail": str(exc), "raw_response": raw[:50000]}
                return
            output.provider_job_id = None
            yield {"type": "complete", "output": output.model_dump()}
            return
        except VideoProviderError:
            raise
        except Exception:
            # SDK versions without streaming support still use the async
            # polling path, keeping the provider contract stable.
            yield {"type": "status", "status": "preparing", "progress": 5, "stage": "准备轮询"}
            output = self.run_generation(request)
            yield {"type": "complete", "output": output.model_dump()}

    def run_generation(self, request: VideoGenerationInput, provider_job_id: str | None = None) -> VideoGenerationOutput:
        self.validate_config()
        run_id = provider_job_id or self.create_generation_job(request)
        if not run_id:
            raise VideoProviderError("Coze 未返回 workflow run id")
        if self._coze is not None:
            try:
                deadline = time.monotonic() + max(1, self.config.coze_timeout_seconds)
                while True:
                    history = self.coze.workflows.runs.run_histories.retrieve(workflow_id=self.config.coze_workflow_id, execute_id=run_id)
                    status = str(getattr(history, "execute_status", "")).lower()
                    if status.endswith("running") and time.monotonic() < deadline:
                        time.sleep(max(0.0, self.config.coze_poll_interval_seconds))
                        continue
                    if status.endswith("running"):
                        raise VideoProviderError("Coze workflow 轮询超时")
                    if status.endswith("fail"):
                        raise VideoProviderError(str(getattr(history, "error_message", "Coze workflow failed")))
                    content = getattr(history, "output", "")
                    output = normalize_output(self.parse_json_content(content))
                    output.provider_job_id = run_id
                    return output
            except VideoProviderError:
                raise
            except Exception:
                pass
        response = self.client.get(f"/v1/workflow/runs/{run_id}", headers=self._headers())
        self.last_request_id = response.headers.get("x-request-id") or response.headers.get("x-log-id") or self.last_request_id
        if response.status_code >= 400:
            raise VideoProviderError(f"Coze workflow 查询失败（HTTP {response.status_code}）")
        body = response.json()
        status = str(body.get("status", "")).lower()
        if status in {"failed", "error"}:
            raise VideoProviderError(str(body.get("error_message") or body.get("error") or "Coze workflow failed"))
        content = body.get("data") or body.get("output") or body.get("result") or body
        try:
            output = normalize_output(self.parse_json_content(content))
        except ValueError as exc:
            raise VideoProviderError(str(exc), raw_response=str(content)[:50000]) from exc
        output.provider_job_id = run_id
        return output

    def cancel_generation(self, provider_job_id: str) -> None:
        self.validate_config()
        response = self.client.post(f"/v1/workflow/runs/{provider_job_id}/cancel", headers=self._headers())
        if response.status_code >= 400 and response.status_code != 404:
            raise VideoProviderError("Coze workflow 取消失败")

    def get_status(self, provider_job_id: str) -> VideoProgress:
        response = self.client.get(f"/v1/workflow/runs/{provider_job_id}", headers=self._headers())
        if response.status_code >= 400:
            raise VideoProviderError("Coze workflow 状态查询失败")
        body = response.json()
        status = str(body.get("status", "preparing")).lower()
        mapped = "completed" if status in {"success", "completed"} else "failed" if status in {"failed", "error"} else "preparing"
        return VideoProgress(status=mapped, progress=100 if mapped == "completed" else 20, stage=status, provider_job_id=provider_job_id, error_message=body.get("error_message"))

    def health_check(self) -> dict[str, Any]:
        configured = bool(self.config.coze_enabled and self.config.coze_api_token and self.config.coze_workflow_id)
        return {"provider": self.name, "configured": configured, "workflow_id_configured": bool(self.config.coze_workflow_id)}
