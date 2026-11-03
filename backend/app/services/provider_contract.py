"""Provider-neutral contracts shared by AI integrations."""

from __future__ import annotations

from typing import Any, Iterable, Protocol


class ProviderError(RuntimeError):
    """Base class for errors that can be mapped consistently at the API edge."""


class ProviderUnavailable(ProviderError):
    """Provider is unreachable; callers may retry."""

    retryable = True


class ProviderTimeout(ProviderError):
    """Provider did not answer in time; callers may retry."""

    retryable = True


class ProviderRateLimited(ProviderError):
    """Provider rejected the call on quota; callers may retry later."""

    retryable = True


class InvalidProviderResponse(ProviderError):
    """Provider replied with a payload the gateway cannot parse."""

    retryable = False


class MissingProviderCapability(ProviderError):
    """Provider cannot serve the capability the business asks for."""

    retryable = False


class ModelProvider(Protocol):
    """Structural contract implemented by every AI integration.

    Implementations raise ``ProviderError`` subclasses; the ``retryable`` flag
    of the raised error decides whether the API edge answers 503 or 502.
    """

    def generate_text(self, system: str, payload: dict[str, Any]) -> str: ...

    def generate_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    # Yields interim chunks followed by one final payload.
    def stream_json(self, system: str, payload: dict[str, Any]) -> Iterable[dict[str, Any]]: ...

    def health_check(self) -> dict[str, Any]: ...
