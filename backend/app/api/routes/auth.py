from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import clear_auth_cookies, hash_password, issue_tokens, set_auth_cookies, verify_password
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas import AuthResponse, LoginIn, RegisterIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    email = str(payload.email).lower()
    if db.scalar(select(User).where(or_(User.username == username, User.email == email))):
        raise HTTPException(status_code=409, detail="Username or email already exists")
    user = User(username=username, email=email, name=(payload.name or username), password_hash=hash_password(payload.password), role=UserRole.student)
    db.add(user)
    db.commit()
    db.refresh(user)
    access, refresh = issue_tokens(user)
    set_auth_cookies(response, access, refresh)
    return {"message": "Account created successfully", "user": user}

@router.post("/login", response_model=AuthResponse)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    identifier = payload.username.strip().lower()
    user = db.scalar(select(User).where(or_(User.username == identifier, User.email == identifier)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    access, refresh = issue_tokens(user)
    set_auth_cookies(response, access, refresh)
    return {"message": "Login successful", "user": user}

@router.post("/logout")
def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "Logged out"}

@router.get("/session", response_model=UserOut)
def session(user: User = Depends(current_user)):
    return user

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user

