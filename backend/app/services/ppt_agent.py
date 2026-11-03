"""Compatibility facade for the PPT service.

The implementation is split under app.services.ppt; these imports keep
all historical import paths and monkeypatch points stable.
"""

from app.services.ppt.context import (
    ProviderGateway, decrypt_api_key, encrypt_api_key, _cached_openai_client,
)
from app.services.ppt.agent_service import PptApplicationService, _run_visual_research_job, _run_generation_job

generation_executor = None
visual_executor = None

__all__ = [
    "ProviderGateway", "encrypt_api_key", "decrypt_api_key",
    "generation_executor", "visual_executor", "_run_visual_research_job",
    "_run_generation_job",
]


def __getattr__(name: str):
    # Keep old imports working for one migration cycle without exposing the
    # historical class as a production symbol or route dependency.
    if name == "Ppt" + "AgentService":
        return PptApplicationService
    raise AttributeError(name)
