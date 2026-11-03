"""Upload validation: file names, extensions, sizes and declared MIME types."""

from pathlib import Path

from app.core.config import settings

SUPPORTED_EXTENSIONS = {".pdf", ".pptx", ".docx", ".xlsx", ".xls", ".txt", ".md", ".markdown", ".csv", ".json", ".png", ".jpg", ".jpeg", ".webp"}


# TODO(comment): verify this helper; ``datetime`` and ``timezone``
# are not imported in this module and no caller uses it today.
def now_utc() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


def _safe_name(filename: str | None) -> str:
    """Reduce a browser-supplied name to its final path component."""
    name = Path(filename or "upload").name.strip() or "upload"
    return name[:500]


def validate_upload(filename: str | None, content_type: str | None, size: int) -> tuple[str, str]:
    """Normalize and validate an upload name, type and size.

    Returns:
        The safe file name and its lowercase extension.

    Raises:
        ValueError: for unsupported extensions, an empty file, a size above the
            limit, or a content type that contradicts the extension.
    """
    name = _safe_name(filename)
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError("仅支持 PDF、PPTX、DOCX、XLSX、TXT、MD、CSV、JSON 和图片文件")
    if size <= 0:
        raise ValueError("文件不能为空")
    if size > settings.file_processing_max_bytes:
        raise ValueError(f"文件不能超过 {settings.file_processing_max_bytes // 1024 // 1024}MB")
    expected = {".pdf": {"application/pdf"}, ".json": {"application/json", "text/json", "text/plain"}, ".csv": {"text/csv", "text/plain"}, ".txt": {"text/plain"}, ".md": {"text/markdown", "text/plain"}, ".markdown": {"text/markdown", "text/plain"}, ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/zip"}, ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"}, ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"}}
    if content_type and content_type not in expected.get(ext, set()) | {"application/octet-stream", "binary/octet-stream"} and not content_type.startswith("image/") and ext not in {".xls"}:
        raise ValueError(f"文件类型与扩展名不匹配：{content_type}")
    return name, ext


__all__ = ["SUPPORTED_EXTENSIONS", "validate_upload"]
