"""Shared PPT service context: enums, crypto helpers and provider gateway.

Every PPT mixin imports this module, so it must stay free of request-scoped
state.  Job runners that reuse these helpers open their own session.
"""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import threading
import base64
import mimetypes
import ipaddress
import socket
from urllib.parse import urlparse
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.ai_gateway import AIGateway
from app.models import (
    PptAgentEvent, PptAgentRun, PptExportJob, PptOutlineVersion, PptPage,
    PptProject, PptRequirement, PptSourceChunk,
    PptSourceCollection, PptSourceDocument, User, PptMessage, PptCheckpoint, PptDocumentVersion, PptGenerationJob,
    FileContextBinding, FileProcessingChunk, FileProcessingDocument, PptEditorAsset,
)
from app.db.session import SessionLocal
from app.services.ppt_theme import preview_filename, get_theme, list_layouts, validate_theme_pack
from app.services.browser_image_search import BrowserImageSearch, build_query
from app.services.image_cache import download_image, validate_public_url
from app.services.visual_search import extract_keywords, query_text, rank_candidates, stable_asset_id
from app.services.clip_ranker import rerank
from app.services.file_processing import bind_document


# Canonical stage and status vocabularies.  The values are stored as plain
# strings inside JSON columns, so changing one needs a data migration.
STAGES = ("init", "outline", "visual", "theme", "layout", "design", "export")
STATUSES = ("empty", "ready", "running", "confirmed", "stale", "failed")
# Compatibility handles retained for callers that imported the old names.  Job
# submission itself is centralized in ``app.jobs.dispatcher``.
generation_executor = None
visual_executor = None
# Project-scoped caches and locks are process-local: they dedupe work inside
# one API process, which is not the same as the cross-worker job guarantees
# provided by the outbox table.
_SOURCE_CONTEXT_CACHE: dict[str, list[dict[str, Any]]] = {}
_SOURCE_CONTEXT_LOCK = threading.Lock()
_GENERATION_LOCKS: dict[str, threading.Lock] = {}
_GENERATION_LOCKS_GUARD = threading.Lock()


def _mask(value: str) -> str:
    if not value:
        return ""
    return f"{value[:4]}••••{value[-4:]}" if len(value) > 8 else "••••••••"


def _cipher():
    # Derive the Fernet key from the JWT secret so a deployment does not need a
    # second secret just to encrypt provider keys at rest.
    try:
        from cryptography.fernet import Fernet
        import base64, hashlib
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret_key.encode()).digest())
        return Fernet(key)
    except ImportError as exc:
        raise RuntimeError("cryptography is required for provider key encryption") from exc


def encrypt_api_key(value: str) -> str:
    """Encrypt a provider API key before it is stored."""
    return _cipher().encrypt(value.encode()).decode()


def decrypt_api_key(value: str) -> str:
    """Decrypt a stored provider key; empty input returns an empty string."""
    if not value:
        return ""
    return _cipher().decrypt(value.encode()).decode()


class ProviderGateway(AIGateway):
    """Backward-compatible PPT gateway backed by the platform AI mapping."""
    def __init__(self, db: Session, user_id: str | None = None, business_code: str = "teacher_ppt_agent"):
        super().__init__(db, business_code)
        from types import SimpleNamespace
        # Read-only view of the resolved model, kept for callers that still
        # read ``gateway.config.model`` after the binding lookup moved here.
        self.config = SimpleNamespace(model=self.model, embedding_model=(self.binding.embedding_model if self.binding else ""))
@lru_cache(maxsize=32)
def _cached_openai_client(api_key: str, base_url: str, timeout: int):
    # Reuse one client per credential and base URL: each client owns an HTTP
    # pool, so building one per request adds a TLS handshake to every call.
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)



# Re-export the helpers so ``from .context import *`` in ``agent_service``
# keeps the historical module surface.
__all__ = [name for name in globals() if name not in {"__builtins__", "__all__"}]
