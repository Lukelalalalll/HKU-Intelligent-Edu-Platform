"""Chunked upload streaming straight into the local storage root."""

import hashlib
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4
from app.core.config import settings

def stream_to_storage(file: BinaryIO, filename: str) -> tuple[str, int, str]:
    """Stream a file into the upload root and hash it.

    Returns:
        Tuple of stored key, byte size and sha256; the partial file is removed
        when the stream exceeds the configured size limit or fails.
    """
    root = settings.upload_path
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{uuid4().hex}{Path(filename).suffix.lower()}"
    digest = hashlib.sha256(); size = 0
    try:
        with target.open("wb") as output:
            while chunk := file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.file_processing_max_bytes:
                    raise ValueError(f"文件不能超过 {settings.file_processing_max_bytes // 1024 // 1024}MB")
                output.write(chunk); digest.update(chunk)
        return target.name, size, digest.hexdigest()
    except Exception:
        target.unlink(missing_ok=True); raise
