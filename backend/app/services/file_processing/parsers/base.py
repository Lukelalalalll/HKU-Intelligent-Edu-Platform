"""Parser contracts and normalized parser results."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class ParseResult:
    """Normalized parser output for one document.

    ``fallback_error`` records why a degraded parser was used so the document
    can be marked ``partial_ready`` instead of ``ready``.
    """
    pages: list[dict[str, Any]]
    parser: str
    parser_version: str = "1"
    fallback_error: str | None = None


class DocumentParser(Protocol):
    """Structural contract implemented by every file-type parser."""
    name: str

    def supports(self, extension: str, mime_type: str | None = None) -> bool: ...

    def parse(self, source: Path, output_dir: Path) -> ParseResult: ...


@dataclass
class ParserRegistry:
    """Ordered parser list resolved by extension and MIME type."""
    parsers: list[DocumentParser] = field(default_factory=list)

    def register(self, parser: DocumentParser) -> None:
        """Append a parser to the resolution order."""
        self.parsers.append(parser)

    def resolve(self, extension: str, mime_type: str | None = None) -> DocumentParser:
        """Return the first parser that supports the input.

        Raises:
            ValueError: when no registered parser matches the extension.
        """
        for parser in self.parsers:
            if parser.supports(extension, mime_type):
                return parser
        raise ValueError(f"No parser registered for {extension}")
