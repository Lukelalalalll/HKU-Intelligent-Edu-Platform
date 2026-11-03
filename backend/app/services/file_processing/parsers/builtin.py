"""Default parser registry and the composite built-in parser."""

from pathlib import Path
from .base import ParseResult, ParserRegistry
from .pdf import PdfParser
from .office import OfficeParser
from .text import TextParser
from .image import ImageParser

class BuiltinParser:
    """Composite parser delegating to the concrete parser by extension."""
    name = "builtin"
    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        """Report whether any concrete parser accepts the extension."""
        return any(p().supports(extension, mime_type) for p in (PdfParser, OfficeParser, TextParser, ImageParser))
    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        """Delegate to the concrete parser resolved for the source suffix."""
        return default_registry().resolve(source.suffix, None).parse(source, output_dir)

def default_registry() -> ParserRegistry:
    """Return a new registry with the built-in parsers registered."""
    registry = ParserRegistry()
    registry.register(PdfParser())
    registry.register(OfficeParser())
    registry.register(TextParser())
    registry.register(ImageParser())
    return registry
