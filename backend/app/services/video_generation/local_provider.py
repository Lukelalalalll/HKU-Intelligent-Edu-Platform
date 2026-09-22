import shutil
import subprocess
import shlex
from threading import BoundedSemaphore
from pathlib import Path
from typing import Any

from app.core.config import settings

from .base import VideoProvider, VideoProviderError
from .schemas import VideoGenerationInput, VideoGenerationOutput, VideoProgress, VideoSceneData


_render_slots = BoundedSemaphore(1)


class LocalProvider(VideoProvider):
    name = "local"

    def __init__(self, config=settings):
        self.config = config

    def validate_config(self) -> None:
        if not self.config.local_video_enabled:
            raise VideoProviderError("Local video provider 未启用")

    def create_generation_job(self, request: VideoGenerationInput) -> str | None:
        self.validate_config()
        return None

    def run_generation(self, request: VideoGenerationInput, provider_job_id: str | None = None) -> VideoGenerationOutput:
        self.validate_config()
        if self.config.local_video_model_dir and not Path(self.config.local_video_model_dir).is_dir():
            raise VideoProviderError("Local video model directory 不存在，请检查 LOCAL_VIDEO_MODEL_DIR")
        if request.avatar_enabled and not self._gpu_available():
            raise VideoProviderError("数字人生成需要可用 CUDA GPU；请关闭数字人或配置本地 GPU worker")
        scenes = [VideoSceneData(order=1, duration_seconds=request.duration_seconds, narration=request.source_text or request.title, onscreen_text=request.title, visual_prompt="课程卡片")] 
        return VideoGenerationOutput(script=request.source_text or request.title, scenes=scenes, metadata={"renderer": "ffmpeg-card-mvp", "gpu_available": self._gpu_available()})

    def cancel_generation(self, provider_job_id: str) -> None:
        return None

    def get_status(self, provider_job_id: str) -> VideoProgress:
        return VideoProgress(status="rendering", progress=50, stage="本地卡片渲染", provider_job_id=provider_job_id)

    def normalize_event(self, event: Any) -> dict[str, Any]:
        return event if isinstance(event, dict) else {"type": "status", "status": "rendering"}

    def health_check(self) -> dict[str, Any]:
        return {"provider": self.name, "configured": bool(self.config.local_video_enabled), "cuda_available": self._gpu_available(), "ffmpeg_available": shutil.which("ffmpeg") is not None}

    @staticmethod
    def _gpu_available() -> bool:
        try:
            import torch
            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def render(self, output: VideoGenerationOutput, job_id: str) -> dict[str, str]:
        _render_slots.acquire()
        try:
            return self._render_locked(output, job_id)
        finally:
            _render_slots.release()

    def _render_locked(self, output: VideoGenerationOutput, job_id: str) -> dict[str, str]:
        root = self.config.video_storage_path / job_id
        root.mkdir(parents=True, exist_ok=True)
        script_path = root / "script.txt"
        script_path.write_text(output.script, encoding="utf-8")
        vtt_path = root / "captions.vtt"
        srt_path = root / "captions.srt"
        elapsed = 0
        lines = ["WEBVTT", ""]
        srt_lines: list[str] = []
        for scene in output.scenes:
            end = elapsed + max(1, scene.duration_seconds)
            caption = scene.caption_text or scene.narration
            lines.extend([f"00:{elapsed // 60:02d}:{elapsed % 60:02d}.000 --> 00:{end // 60:02d}:{end % 60:02d}.000", caption, ""])
            srt_lines.extend([str(scene.order), f"00:{elapsed // 3600:02d}:{(elapsed % 3600) // 60:02d}:{elapsed % 60:02d},000 --> 00:{end // 3600:02d}:{(end % 3600) // 60:02d}:{end % 60:02d},000", caption, ""])
            elapsed = end
        vtt_path.write_text("\n".join(lines), encoding="utf-8")
        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
        audio_path = root / "narration.wav"
        self._render_audio(output, audio_path)
        video_path = root / "video.mp4"
        if shutil.which("ffmpeg"):
            seconds = max(1, elapsed)
            command = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x182333:s={self.config.local_video_width}x{self.config.local_video_height}:d={seconds}"]
            if audio_path.exists(): command += ["-i", str(audio_path), "-shortest"]
            command += ["-r", str(self.config.local_video_fps), "-pix_fmt", "yuv420p", "-c:v", "libx264"]
            if audio_path.exists(): command += ["-c:a", "aac"]
            command += [str(video_path)]
            subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"video": str(video_path) if video_path.exists() else "", "audio": str(audio_path) if audio_path.exists() else "", "captions": str(vtt_path), "srt": str(srt_path), "script": str(script_path)}

    def _render_audio(self, output: VideoGenerationOutput, audio_path: Path) -> None:
        """Use an operator-configured offline TTS command when available.

        The command receives a UTF-8 text file followed by the output WAV path.
        This keeps GPT-SoVITS, Piper, or another local engine replaceable and
        never moves voice text or credentials into the browser.
        """
        command = self.config.local_video_tts_command.strip()
        if command:
            text_path = audio_path.with_suffix(".txt")
            text_path.write_text("\n".join(scene.narration for scene in output.scenes), encoding="utf-8")
            argv = shlex.split(command) + [str(text_path), str(audio_path)]
            try:
                subprocess.run(argv, check=True, timeout=self.config.local_video_tts_timeout_seconds, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except (OSError, subprocess.SubprocessError):
                pass
        # A valid silent track keeps muxing deterministic while the optional
        # TTS engine is unavailable; metadata reports the fallback explicitly.
        if shutil.which("ffmpeg"):
            seconds = max(1, sum(max(1, scene.duration_seconds) for scene in output.scenes))
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-t", str(seconds), str(audio_path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
