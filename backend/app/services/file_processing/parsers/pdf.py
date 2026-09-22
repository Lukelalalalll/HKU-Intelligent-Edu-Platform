from pathlib import Path

from app.services.file_processing_legacy import _mineru_pdf, _native_pdf
from .base import ParseResult


class PdfParser:
    name = "pdf"

    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        return extension.lower() == ".pdf"

    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        try:
            return ParseResult(_mineru_pdf(source, output_dir), "mineru")
        except Exception as exc:
            return ParseResult(_native_pdf(source), "native_pdf_fallback", fallback_error=str(exc)[:2000])
