"""Provider-neutral contracts shared by AI integrations."""

from __future__ import annotations

from typing import Any, Iterable, Protocol


class ProviderError(RuntimeError):
    """Base class for errors that can be mapped consistently at the API edge."""


class ProviderUnavailable(ProviderError):
    retryable = True


class ProviderTimeout(ProviderError):
    retryable = True


class ProviderRateLimited(ProviderError):
    retryable = True


class InvalidProviderResponse(ProviderError):
    retryable = False


class MissingProviderCapability(ProviderError):
    retryable = False


class ModelProvider(Protocol):
    def generate_text(self, system: str, payload: dict[str, Any]) -> str: ...

    def generate_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def stream_json(self, system: str, payload: dict[str, Any]) -> Iterable[dict[str, Any]]: ...

    def health_check(self) -> dict[str, Any]: ...
