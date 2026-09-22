from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from .schemas import VideoGenerationInput, VideoGenerationOutput, VideoProgress


class VideoProviderError(RuntimeError):
    """A provider error safe to show to a teacher."""

    def __init__(self, message: str, *, raw_response: str | None = None):
        super().__init__(message)
        self.raw_response = raw_response


class VideoProvider(ABC):
    name: str

    @abstractmethod
    def validate_config(self) -> None: ...

    @abstractmethod
    def create_generation_job(self, request: VideoGenerationInput) -> str | None: ...

    @abstractmethod
    def run_generation(self, request: VideoGenerationInput, provider_job_id: str | None = None) -> VideoGenerationOutput: ...

    @abstractmethod
    def cancel_generation(self, provider_job_id: str) -> None: ...

    @abstractmethod
    def get_status(self, provider_job_id: str) -> VideoProgress: ...

    @abstractmethod
    def normalize_event(self, event: Any) -> dict[str, Any]: ...

    @abstractmethod
    def health_check(self) -> dict[str, Any]: ...

    def stream_generation(self, request: VideoGenerationInput) -> Iterable[dict[str, Any]]:
        yield {"type": "status", "status": "preparing", "progress": 5, "stage": "准备生成"}
        output = self.run_generation(request)
        yield {"type": "complete", "output": output.model_dump()}
