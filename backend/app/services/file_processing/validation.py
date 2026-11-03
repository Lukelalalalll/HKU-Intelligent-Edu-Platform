from pathlib import Path

from app.core.config import settings

SUPPORTED_EXTENSIONS = {".pdf", ".pptx", ".docx", ".xlsx", ".xls", ".txt", ".md", ".markdown", ".csv", ".json", ".png", ".jpg", ".jpeg", ".webp"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _safe_name(filename: str | None) -> str:
    name = Path(filename or "upload").name.strip() or "upload"
    return name[:500]


def validate_upload(filename: str | None, content_type: str | None, size: int) -> tuple[str, str]:
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
