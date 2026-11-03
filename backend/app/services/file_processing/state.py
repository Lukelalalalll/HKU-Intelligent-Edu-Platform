"""Document and job state vocabularies used by the processing pipeline."""

from __future__ import annotations
from datetime import datetime, timezone

# Statuses persisted on ``FileProcessingDocument.status``.
DOCUMENT_STATES = {"queued", "processing", "ready", "partial_ready", "failed"}
# Statuses persisted on ``FileProcessingJob.status``.
JOB_STATES = {"queued", "running", "completed", "failed", "cancelled"}
# Statuses that mean a worker still owns the job.
ACTIVE_JOB_STATES = {"queued", "running"}

def now_utc() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)

def transition_document(document, status: str) -> None:
    """Set a document status after validating the vocabulary."""
    if status not in DOCUMENT_STATES:
        raise ValueError(f"invalid document status: {status}")
    document.status = status
