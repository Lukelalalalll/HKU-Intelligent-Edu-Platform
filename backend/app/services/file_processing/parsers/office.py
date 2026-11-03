"""Office parsers for PPTX, DOCX and workbook files."""

from pathlib import Path
from .base import ParseResult
from .utils import _office_fallback, _office_pages

OFFICE_EXTENSIONS = {".pptx", ".docx", ".xlsx", ".xls"}
class OfficeParser:
    """Parse Office containers with the optional native libraries."""
    name = "office"
    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        """Accept the Office extensions this parser handles."""
        return extension.lower() in OFFICE_EXTENSIONS
    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        """Parse with native OOXML readers, falling back to zip/XML text.

        The fallback keeps ingestion working in deployments without the optional
        Office libraries, at lower extraction confidence.
        """
        try:
            return ParseResult(_office_pages(source), "native_office", "1")
        except Exception as exc:
            return ParseResult(_office_fallback(source), "native_office_fallback", "1", str(exc)[:2000])
