from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import FileAsset, User
from app.storage import LocalStorage

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_BYTES = 5 * 1024 * 1024


def update_profile(db: Session, user: User, name: str | None, email: str | None) -> User:
    if name is not None:
        normalized_name = name.strip()
        if not normalized_name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name cannot be empty")
        user.name = normalized_name
    if email is not None:
        normalized_email = email.strip().lower()
        if db.scalar(select(User).where(User.email == normalized_email, User.id != user.id)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
        user.email = normalized_email
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if current_password == new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")
    user.password_hash = hash_password(new_password)
    db.commit()


def _stored_avatar_key(avatar_url: str | None) -> str | None:
    if not avatar_url:
        return None
    key = avatar_url.rsplit("/", 1)[-1]
    return key if key and Path(key).name == key else None


def replace_avatar(db: Session, user: User, upload: UploadFile, storage: LocalStorage) -> User:
    if upload.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Avatar must be JPEG, PNG, or WebP")
    content = upload.file.read(MAX_AVATAR_BYTES + 1)
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Avatar must be 5 MB or smaller")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Avatar file is empty")

    old_key = _stored_avatar_key(user.avatar_url)
    key = size = digest = None
    try:
        key, size, digest = storage.save(upload.filename or "avatar", content)
        asset = FileAsset(
            original_name=upload.filename or "avatar",
            mime_type=upload.content_type,
            extension=Path(upload.filename or "").suffix.lower(),
            size_bytes=size,
            sha256=digest,
            storage_key=key,
            uploader_id=user.id,
        )
        db.add(asset)
        user.avatar_url = storage.get_url(key)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        if key:
            storage.delete(key)
        raise

    if old_key and old_key != key:
        old_asset = db.scalar(select(FileAsset).where(FileAsset.storage_key == old_key, FileAsset.uploader_id == user.id))
        if old_asset:
            db.delete(old_asset)
            db.commit()
        storage.delete(old_key)
    return user


def remove_avatar(db: Session, user: User, storage: LocalStorage) -> User:
    old_key = _stored_avatar_key(user.avatar_url)
    user.avatar_url = None
    db.commit()
    db.refresh(user)
    if old_key:
        old_asset = db.scalar(select(FileAsset).where(FileAsset.storage_key == old_key, FileAsset.uploader_id == user.id))
        if old_asset:
            db.delete(old_asset)
            db.commit()
        storage.delete(old_key)
    return user
