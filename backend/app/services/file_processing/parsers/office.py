from pathlib import Path

from app.services.file_processing_legacy import _office_fallback, _office_pages
from .base import ParseResult


OFFICE_EXTENSIONS = {".pptx", ".docx", ".xlsx", ".xls"}


class OfficeParser:
    name = "office"

    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        return extension.lower() in OFFICE_EXTENSIONS

    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        try:
            return ParseResult(_office_pages(source), "native_office")
        except Exception as exc:
            return ParseResult(_office_fallback(source), "native_office_fallback", fallback_error=str(exc)[:2000])
