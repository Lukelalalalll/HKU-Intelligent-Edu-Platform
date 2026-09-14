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
from app.services.file_processing import upload_asset

router = APIRouter(prefix="/api/files", tags=["files"])

@router.post("", status_code=201)
def upload_file(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    content = file.file.read()
    try:
        asset, document, job = upload_asset(db, uploader_id=user.id, filename=file.filename or "upload", mime_type=file.content_type, content=content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": asset.id, "name": asset.original_name, "size_bytes": asset.size_bytes, "storage_key": asset.storage_key, "url": LocalStorage(settings.upload_path).get_url(asset.storage_key), "document_id": document.id, "job_id": job.id if job else None, "processing_status": document.status}

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
