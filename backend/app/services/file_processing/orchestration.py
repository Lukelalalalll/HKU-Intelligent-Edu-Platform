"""Application-level orchestration for document parsing."""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.services.file_processing.parsers.base import ParseResult
from app.services.file_processing.parsers.builtin import default_registry


def parse_document(source: Path, output_dir: Path, mime_type: str | None = None) -> ParseResult:
    """Resolve a parser by capability and normalize its output."""
    parser = default_registry().resolve(source.suffix, mime_type)
    return parser.parse(source, output_dir)


def processing_root(document_id: str) -> Path:
    return settings.file_processing_path / document_id
