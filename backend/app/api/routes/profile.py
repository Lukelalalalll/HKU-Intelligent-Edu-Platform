from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.schemas import PasswordChangeIn, ProfileUpdateIn, UserOut
from app.services.profile import change_password, remove_avatar, replace_avatar, update_profile
from app.storage import LocalStorage

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=UserOut)
def get_profile(user: User = Depends(current_user)):
    return user


@router.patch("", response_model=UserOut)
def patch_profile(payload: ProfileUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return update_profile(db, user, payload.name, payload.email)


@router.post("/avatar", response_model=UserOut)
def upload_avatar(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    return replace_avatar(db, user, file, LocalStorage(settings.upload_path))


@router.delete("/avatar", response_model=UserOut)
def delete_avatar(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return remove_avatar(db, user, LocalStorage(settings.upload_path))


@router.put("/password", status_code=204)
def put_password(payload: PasswordChangeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    change_password(db, user, payload.current_password, payload.new_password)
