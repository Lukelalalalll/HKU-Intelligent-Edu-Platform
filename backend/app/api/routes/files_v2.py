"""Task-oriented file API used by the v2 clients."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.services.file_processing import upload_asset_stream


router = APIRouter(prefix="/api/v2/files", tags=["files-v2"])


@router.post("", status_code=202)
def upload_file_v2(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        asset, document, job = upload_asset_stream(db, uploader_id=user.id, filename=file.filename or "upload", mime_type=file.content_type, file=file.file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"asset_id": asset.id, "document_id": document.id, "job_id": job.id if job else None, "status": document.status, "storage_key": asset.storage_key, "url": f"/api/files/{asset.storage_key}", "max_bytes": settings.file_processing_max_bytes}
