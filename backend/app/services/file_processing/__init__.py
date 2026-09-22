"""Public file-processing application boundary.

The compatibility exports remain stable while new code can depend on the
parser registry and orchestration APIs without importing the legacy module.
"""

from app.services.file_processing_legacy import (
    bind_document, enqueue_job, ensure_document_for_asset, process_job,
    recover_jobs, upload_asset, validate_upload, _office_pages, _pages_to_chunks,
)
from app.services.file_processing.orchestration import parse_document
from app.services.file_processing.parsers import DocumentParser, ParseResult, ParserRegistry, default_registry
from app.services.file_processing.repository import upload_asset_stream

__all__ = [
    "bind_document", "enqueue_job", "ensure_document_for_asset",
    "process_job", "recover_jobs", "upload_asset", "validate_upload",
    "_office_pages", "_pages_to_chunks",
    "parse_document", "DocumentParser", "ParseResult", "ParserRegistry", "default_registry",
    "upload_asset_stream",
]
