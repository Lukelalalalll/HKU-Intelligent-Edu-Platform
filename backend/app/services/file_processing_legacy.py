"""Deprecated compatibility wrappers for the file-processing service."""
from .file_processing.validation import SUPPORTED_EXTENSIONS, validate_upload
from .file_processing.repository import bind_document, ensure_document_for_asset, upload_asset, upload_asset_stream
from .file_processing.orchestration import enqueue_job, process_job, recover_jobs
from .file_processing.parsers.utils import _block, _native_pdf, _mineru_pdf, _office_pages, _office_fallback, _pages_to_chunks
__all__ = ["SUPPORTED_EXTENSIONS", "validate_upload", "bind_document", "ensure_document_for_asset", "upload_asset", "upload_asset_stream", "enqueue_job", "process_job", "recover_jobs"]
