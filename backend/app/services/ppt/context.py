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
from app.services.file_processing import upload_asset, bind_document


STAGES = ("init", "outline", "visual", "theme", "layout", "design", "export")
STATUSES = ("empty", "ready", "running", "confirmed", "stale", "failed")
# Compatibility handles retained for callers that imported the old names.  Job
# submission itself is centralized in ``app.jobs.dispatcher``.
generation_executor = None
visual_executor = None
_SOURCE_CONTEXT_CACHE: dict[str, list[dict[str, Any]]] = {}
_SOURCE_CONTEXT_LOCK = threading.Lock()
_GENERATION_LOCKS: dict[str, threading.Lock] = {}
_GENERATION_LOCKS_GUARD = threading.Lock()


def _mask(value: str) -> str:
    if not value:
        return ""
    return f"{value[:4]}••••{value[-4:]}" if len(value) > 8 else "••••••••"


def _cipher():
    try:
        from cryptography.fernet import Fernet
        import base64, hashlib
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret_key.encode()).digest())
        return Fernet(key)
    except ImportError:
        # Keep the app runnable before optional wheels are installed; production
        # requirements include cryptography/Fernet.
        import base64, hashlib
        key = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
        class LocalCipher:
            def encrypt(self, value: bytes) -> bytes:
                return base64.urlsafe_b64encode(bytes(v ^ key[i % len(key)] for i, v in enumerate(value)))
            def decrypt(self, value: bytes) -> bytes:
                raw = base64.urlsafe_b64decode(value)
                return bytes(v ^ key[i % len(key)] for i, v in enumerate(raw))
        return LocalCipher()


def encrypt_api_key(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode()


def decrypt_api_key(value: str) -> str:
    if not value:
        return ""
    return _cipher().decrypt(value.encode()).decode()


class ProviderGateway(AIGateway):
    """Backward-compatible PPT gateway backed by the platform AI mapping."""
    def __init__(self, db: Session, user_id: str | None = None, business_code: str = "teacher_ppt_agent"):
        super().__init__(db, business_code)
        from types import SimpleNamespace
        self.config = SimpleNamespace(model=self.model, embedding_model=(self.binding.embedding_model if self.binding else ""))
@lru_cache(maxsize=32)
def _cached_openai_client(api_key: str, base_url: str, timeout: int):
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)



__all__ = [name for name in globals() if name not in {"__builtins__", "__all__"}]
