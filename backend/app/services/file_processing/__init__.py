"""File processing compatibility package.

The legacy implementation remains private to this package while callers keep
the historical ``app.services.file_processing`` exports.
"""

from app.services.file_processing_legacy import (
    bind_document, enqueue_job, ensure_document_for_asset, process_job,
    recover_jobs, upload_asset, validate_upload, _office_pages, _pages_to_chunks,
)

__all__ = [
    "bind_document", "enqueue_job", "ensure_document_for_asset",
    "process_job", "recover_jobs", "upload_asset", "validate_upload",
    "_office_pages", "_pages_to_chunks",
]
