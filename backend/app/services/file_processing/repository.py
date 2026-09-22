from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import FileAsset
from app.services.file_processing.storage import stream_to_storage
from app.services.file_processing_legacy import bind_document, ensure_document_for_asset, upload_asset
from app.services.file_processing.validation import validate_upload


def upload_asset_stream(
    db: Session,
    *,
    uploader_id: str,
    filename: str,
    mime_type: str | None,
    file: BinaryIO,
    target_type: str | None = None,
    target_id: str | None = None,
    owner_id: str | None = None,
    course_id: str | None = None,
    visibility: str = "owner",
    metadata: dict | None = None,
):
    """Persist an upload in bounded chunks before creating its DB metadata."""
    # Validate cheap metadata before touching disk; size is checked after the
    # stream has been measured so callers do not need to buffer the payload.
    validate_upload(filename, mime_type, 1)
    name, ext = validate_upload(filename, mime_type, 1)
    key, size, digest = stream_to_storage(file, name)
    try:
        validate_upload(name, mime_type, size)
        asset = db.scalar(select(FileAsset).where(FileAsset.uploader_id == uploader_id, FileAsset.sha256 == digest, FileAsset.original_name == name))
        if asset:
            (settings.upload_path / key).unlink(missing_ok=True)
        else:
            asset = FileAsset(original_name=name, mime_type=mime_type or "application/octet-stream", extension=ext, size_bytes=size, sha256=digest, storage_key=key, uploader_id=uploader_id, course_id=course_id)
            db.add(asset)
            db.flush()
        document, job = ensure_document_for_asset(db, asset, target_type=target_type, target_id=target_id, owner_id=owner_id or uploader_id, course_id=course_id, visibility=visibility, metadata=metadata)
        return asset, document, job
    except Exception:
        (settings.upload_path / key).unlink(missing_ok=True)
        raise

__all__ = ["bind_document", "ensure_document_for_asset", "upload_asset", "upload_asset_stream"]
