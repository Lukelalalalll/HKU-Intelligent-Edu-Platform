from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import FileAsset, User
from app.storage import LocalStorage

router = APIRouter(prefix="/api/files", tags=["files"])

@router.post("", status_code=201)
def upload_file(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    content = file.file.read()
    storage = LocalStorage(settings.upload_path)
    key, size, digest = storage.save(file.filename or "upload", content)
    asset = FileAsset(original_name=file.filename or "upload", mime_type=file.content_type or "application/octet-stream", extension=Path(file.filename or "").suffix.lower(), size_bytes=size, sha256=digest, storage_key=key, uploader_id=user.id)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"id": asset.id, "name": asset.original_name, "size_bytes": asset.size_bytes, "storage_key": key, "url": storage.get_url(key)}

@router.get("/{storage_key}")
def download_file(storage_key: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if Path(storage_key).name != storage_key:
        raise HTTPException(status_code=404, detail="File not found")
    asset = db.scalar(select(FileAsset).where(FileAsset.storage_key == storage_key))
    if not asset or (asset.uploader_id != user.id and user.role.value != "admin"):
        raise HTTPException(status_code=404, detail="File not found")
    path = settings.upload_path / storage_key
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type=asset.mime_type, filename=asset.original_name)
