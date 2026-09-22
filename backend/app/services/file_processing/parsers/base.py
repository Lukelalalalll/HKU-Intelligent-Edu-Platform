"""Parser contracts and normalized parser results."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class ParseResult:
    pages: list[dict[str, Any]]
    parser: str
    parser_version: str = "1"
    fallback_error: str | None = None


class DocumentParser(Protocol):
    name: str

    def supports(self, extension: str, mime_type: str | None = None) -> bool: ...

    def parse(self, source: Path, output_dir: Path) -> ParseResult: ...


@dataclass
class ParserRegistry:
    parsers: list[DocumentParser] = field(default_factory=list)

    def register(self, parser: DocumentParser) -> None:
        self.parsers.append(parser)

    def resolve(self, extension: str, mime_type: str | None = None) -> DocumentParser:
        for parser in self.parsers:
            if parser.supports(extension, mime_type):
                return parser
        raise ValueError(f"No parser registered for {extension}")
