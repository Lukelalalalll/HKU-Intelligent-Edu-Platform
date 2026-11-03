"""Plain text, Markdown, CSV and JSON parser."""

from pathlib import Path
from .base import ParseResult
from .utils import _office_pages
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json"}
class TextParser:
    """Read UTF-8 text formats through the shared text extractor."""
    name = "text"
    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        """Accept the text extensions this parser handles."""
        return extension.lower() in TEXT_EXTENSIONS
    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        """Return the file content as a single page."""
        return ParseResult(_office_pages(source), "native_text", "1")
