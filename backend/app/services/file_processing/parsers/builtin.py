from pathlib import Path
from .base import ParseResult, ParserRegistry
from .pdf import PdfParser
from .office import OfficeParser
from .text import TextParser
from .image import ImageParser

class BuiltinParser:
    name = "builtin"
    def supports(self, extension: str, mime_type: str | None = None) -> bool:
        return any(p().supports(extension, mime_type) for p in (PdfParser, OfficeParser, TextParser, ImageParser))
    def parse(self, source: Path, output_dir: Path) -> ParseResult:
        return default_registry().resolve(source.suffix, None).parse(source, output_dir)

def default_registry() -> ParserRegistry:
    registry = ParserRegistry()
    registry.register(PdfParser())
    registry.register(OfficeParser())
    registry.register(TextParser())
    registry.register(ImageParser())
    return registry
