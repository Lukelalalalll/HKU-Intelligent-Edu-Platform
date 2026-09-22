from pathlib import Path

from app.services.file_processing_legacy import _office_pages
from .base import ParseResult


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json"}


class TextParser:
    name = "text"

    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        return extension.lower() in TEXT_EXTENSIONS

    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        return ParseResult(_office_pages(source), "native_text")
