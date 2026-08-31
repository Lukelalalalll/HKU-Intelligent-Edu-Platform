from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import clear_auth_cookies, hash_password, issue_tokens, set_auth_cookies, verify_password
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas import AuthResponse, LoginIn, RegisterIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_payload(request: Request, response: Response, user: User, access: str, refresh: str, message: str):
    if request.headers.get("X-HKU-Session-Mode") == "isolated":
        return {"message": message, "user": user, "access_token": access}
    set_auth_cookies(response, access, refresh)
    return {"message": message, "user": user}

@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    email = str(payload.email).lower()
    if db.scalar(select(User).where(or_(User.username == username, User.email == email))):
        raise HTTPException(status_code=409, detail="Username or email already exists")
    user = User(username=username, email=email, name=(payload.name or username), password_hash=hash_password(payload.password), role=UserRole.student)
    db.add(user)
    db.commit()
    db.refresh(user)
    access, refresh = issue_tokens(user)
    return _auth_payload(request, response, user, access, refresh, "Account created successfully")

@router.post("/login", response_model=AuthResponse)
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    identifier = payload.username.strip().lower()
    user = db.scalar(select(User).where(or_(User.username == identifier, User.email == identifier)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    access, refresh = issue_tokens(user)
    return _auth_payload(request, response, user, access, refresh, "Login successful")

@router.post("/logout")
def logout(request: Request, response: Response):
    # Isolated sessions are held in the calling tab's sessionStorage.  Do not
    # delete the host-wide fallback cookie on behalf of another tab.
    if request.headers.get("X-HKU-Session-Mode") != "isolated":
        clear_auth_cookies(response)
    return {"message": "Logged out"}

@router.get("/session", response_model=UserOut)
def session(user: User = Depends(current_user)):
    return user

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
