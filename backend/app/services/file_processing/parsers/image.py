"""Image parser: keeps an image upload as a single original block."""

from pathlib import Path
from .base import ParseResult
from .utils import _block
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
class ImageParser:
    """Treat an image upload as one page with an original block."""
    name = "image"
    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        """Accept image extensions and image MIME types."""
        return extension.lower() in IMAGE_EXTENSIONS or bool(mime_type and mime_type.startswith("image/"))
    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        """Return one synthetic page so image assets still get a chunk."""
        return ParseResult([{"page": 1, "width": 0, "height": 0, "blocks": [_block(1, 1, "image", "", "original", .9)]}], "original_image", "1")
