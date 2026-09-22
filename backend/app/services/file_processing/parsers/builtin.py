"""Built-in adapters around the existing extraction implementation."""

from pathlib import Path

from .base import ParseResult
from app.services.file_processing_legacy import _mineru_pdf, _native_pdf, _office_fallback, _office_pages, _block


class BuiltinParser:
    name = "builtin"

    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        return extension.lower() in {".pdf", ".pptx", ".docx", ".xlsx", ".xls", ".txt", ".md", ".markdown", ".csv", ".json", ".png", ".jpg", ".jpeg", ".webp"}

    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        extension = source.suffix.lower()
        fallback_error = None
        if extension == ".pdf":
            try:
                return ParseResult(_mineru_pdf(source, output_dir), "mineru")
            except Exception as exc:
                fallback_error = str(exc)[:2000]
                return ParseResult(_native_pdf(source), "native_pdf_fallback", fallback_error=fallback_error)
        if extension in {".pptx", ".docx", ".xlsx", ".xls", ".txt", ".md", ".markdown", ".csv", ".json"}:
            try:
                return ParseResult(_office_pages(source), "native_office")
            except Exception as exc:
                fallback_error = str(exc)[:2000]
                pages = _office_fallback(source) if extension in {".pptx", ".docx", ".xlsx", ".xls"} else _office_pages(source)
                return ParseResult(pages, "native_office_fallback", fallback_error=fallback_error)
        return ParseResult([{"page": 1, "width": 0, "height": 0, "blocks": [_block(1, 1, "image", "", "original", .9)]}], "original_image")


def default_registry() -> "ParserRegistry":
    from .base import ParserRegistry
    from .image import ImageParser
    from .office import OfficeParser
    from .pdf import PdfParser
    from .text import TextParser

    registry = ParserRegistry()
    registry.register(PdfParser())
    registry.register(OfficeParser())
    registry.register(TextParser())
    registry.register(ImageParser())
    return registry
