"""Best-effort plain-text extraction shared by the teaching agents.

The PPT agent and the lesson-plan agent both accept teacher material and need a
synchronous text preview that does not depend on the background processing
worker.  Extraction is intentionally forgiving: an unsupported or unreadable
file returns an empty string (or a short hint) so the upload itself succeeds and
the teacher can still describe the content in the conversation.
"""

from __future__ import annotations

from pathlib import Path

TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".csv"}


def read_text_file(path: Path, content: bytes | None = None) -> str:
    """Return decoded UTF-8 text for a plain-text file."""
    raw = content if content is not None else path.read_bytes()
    return raw.decode("utf-8", errors="ignore")


def extract_text(path: Path, content: bytes | None = None, mime_type: str | None = None) -> str:
    """Extract readable text from a supported document.

    Args:
        path: Source path; only the suffix and contents are used.
        content: Original bytes when the caller already holds them.
        mime_type: Reserved for future parser selection.

    Returns:
        Extracted text, or an empty string when the format is unsupported or
        the optional parser is unavailable.
    """
    suffix = path.suffix.lower()
    try:
        if suffix in TEXT_SUFFIXES:
            return read_text_file(path, content)
        if suffix == ".json":
            import json

            raw = read_text_file(path, content)
            try:
                return json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
            except (ValueError, TypeError):
                return raw
        if suffix in {".xlsx", ".xls"}:
            return _extract_xlsx(path)
        if suffix == ".pdf":
            return _extract_pdf(path)
        if suffix == ".docx":
            return _extract_docx(path)
        if suffix == ".pptx":
            return _extract_pptx(path)
    except Exception:
        return ""
    return ""


def _extract_xlsx(path: Path) -> str:
    from openpyxl import load_workbook

    book = load_workbook(path, read_only=True, data_only=True)
    try:
        return "\n".join(
            " | ".join(str(value or "") for value in row)
            for sheet in book.worksheets
            for row in sheet.iter_rows(values_only=True)
        )
    finally:
        book.close()


def _extract_pdf(path: Path) -> str:
    try:
        import pypdf

        text = "\n".join((page.extract_text() or "") for page in pypdf.PdfReader(str(path)).pages).strip()
    except Exception:
        text = ""
    if text:
        return text
    # PyMuPDF is a faster native fallback for PDFs pypdf cannot read.
    try:
        import fitz

        document = fitz.open(str(path))
        try:
            return "\n".join(page.get_text() for page in document).strip()
        finally:
            document.close()
    except Exception:
        return ""


def _extract_docx(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _extract_pptx(path: Path) -> str:
    from pptx import Presentation

    presentation = Presentation(str(path))
    lines: list[str] = []
    for index, slide in enumerate(presentation.slides, 1):
        slide_lines = [
            shape.text.strip()
            for shape in slide.shapes
            if hasattr(shape, "text") and shape.text and shape.text.strip()
        ]
        if slide_lines:
            lines.append(f"第 {index} 页")
            lines.extend(slide_lines)
    return "\n".join(lines)


def truncate_text(text: str, limit: int) -> tuple[str, bool]:
    """Return text capped at ``limit`` characters and whether it was cut."""
    value = text or ""
    if len(value) <= limit:
        return value, False
    return value[:limit], True


__all__ = ["TEXT_SUFFIXES", "extract_text", "read_text_file", "truncate_text"]
