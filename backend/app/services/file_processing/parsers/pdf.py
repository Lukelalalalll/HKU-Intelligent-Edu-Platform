from pathlib import Path
from .base import ParseResult
from .utils import _mineru_pdf, _native_pdf

class PdfParser:
    name = "pdf"
    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        return extension.lower() == ".pdf"
    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        try:
            return ParseResult(_mineru_pdf(source, output_dir), "mineru", "1")
        except Exception as exc:
            return ParseResult(_native_pdf(source), "native_pdf_fallback", "1", str(exc)[:2000])
