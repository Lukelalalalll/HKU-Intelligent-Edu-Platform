"""Stable public file-processing application boundary."""
from .validation import SUPPORTED_EXTENSIONS, validate_upload
from .repository import bind_document, ensure_document_for_asset, upload_asset, upload_asset_stream
from .orchestration import parse_document, process_job, recover_jobs
from .tasks import enqueue_job
from .parsers import DocumentParser, ParseResult, ParserRegistry, default_registry
__all__ = ["SUPPORTED_EXTENSIONS", "validate_upload", "bind_document", "ensure_document_for_asset", "upload_asset", "upload_asset_stream", "enqueue_job", "process_job", "recover_jobs", "parse_document", "DocumentParser", "ParseResult", "ParserRegistry", "default_registry"]


def __getattr__(name):
    """Resolve private parser helpers for pre-migration callers only."""
    if name in {"_office_pages", "_pages_to_chunks"}:
        from .parsers import utils
        return getattr(utils, name)
    raise AttributeError(name)
