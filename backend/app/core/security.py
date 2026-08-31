from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_COOKIE = "hku_access"
REFRESH_COOKIE = "hku_refresh"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def _token(user: User, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user.id, "role": user.role.value, "type": token_type, "iat": now, "exp": now + expires_delta}, settings.jwt_secret_key, algorithm="HS256")

def issue_tokens(user: User) -> tuple[str, str]:
    return _token(user, timedelta(minutes=settings.jwt_access_minutes), "access"), _token(user, timedelta(days=settings.jwt_refresh_days), "refresh")

def set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    common = {"httponly": True, "secure": settings.cookie_secure, "samesite": "lax", "path": "/"}
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=settings.jwt_access_minutes * 60, **common)
    response.set_cookie(REFRESH_COOKIE, refresh_token, max_age=settings.jwt_refresh_days * 86400, **common)

def clear_auth_cookies(response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")


def isolated_access_token(request: Request) -> str | None:
    """Return the bearer token for a frontend-managed isolated session.

    Browsers scope cookies to a host, not a port or tab.  The development
    frontend therefore marks its requests and keeps the token in
    sessionStorage (which is isolated per tab).  Marked requests must never
    fall back to the shared cookie, otherwise an old tab could authenticate
    as whichever account most recently changed the cookie.
    """
    if request.headers.get("X-HKU-Session-Mode") != "isolated":
        return None
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return token


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = isolated_access_token(request) or request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise ValueError
        user = db.get(User, payload.get("sub"))
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")
    return user

def require_roles(*roles: UserRole):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")
        return user
    return dependency
