from __future__ import annotations
from datetime import datetime, timezone

DOCUMENT_STATES = {"queued", "processing", "ready", "partial_ready", "failed"}
JOB_STATES = {"queued", "running", "completed", "failed", "cancelled"}
ACTIVE_JOB_STATES = {"queued", "running"}

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def transition_document(document, status: str) -> None:
    if status not in DOCUMENT_STATES:
        raise ValueError(f"invalid document status: {status}")
    document.status = status
