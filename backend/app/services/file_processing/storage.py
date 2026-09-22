"""File storage operations kept separate from parsing and persistence."""

import hashlib
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings


def stream_to_storage(file: BinaryIO, filename: str) -> tuple[str, int, str]:
    """Write an upload in bounded chunks and return key, size and digest."""
    root = settings.upload_path
    suffix = Path(filename).suffix.lower()
    key = f"{__import__('uuid').uuid4().hex}{suffix}"
    target = root / key
    digest = hashlib.sha256()
    size = 0
    with target.open("wb") as output:
        while chunk := file.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
            size += len(chunk)
            if size > settings.file_processing_max_bytes:
                output.close()
                target.unlink(missing_ok=True)
                raise ValueError(f"文件不能超过 {settings.file_processing_max_bytes // 1024 // 1024}MB")
    return key, size, digest.hexdigest()
