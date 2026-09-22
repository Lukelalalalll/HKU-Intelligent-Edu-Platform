from pathlib import Path

from app.services.file_processing_legacy import _block
from .base import ParseResult


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class ImageParser:
    name = "image"

    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        return extension.lower() in IMAGE_EXTENSIONS or bool(mime_type and mime_type.startswith("image/"))

    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        return ParseResult([{"page": 1, "width": 0, "height": 0, "blocks": [_block(1, 1, "image", "", "original", .9)]}], "original_image")
