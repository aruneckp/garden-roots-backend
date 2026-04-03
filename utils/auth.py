import os
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, Depends, Header
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import AdminUser, User

# Get JWT secret from environment
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def create_access_token(user_id: int, username: str, role: str) -> str:
    """Create JWT access token."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": expires,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def create_user_token(user_id: int, email: str, role: str = "customer") -> str:
    """Create JWT access token for a customer user."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": expires,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_delivery_token(delivery_boy_id: int, username: str) -> str:
    """Create JWT access token for a delivery boy."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": delivery_boy_id,
        "username": username,
        "role": "delivery_boy",
        "exp": expires,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated customer user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    try:
        payload = verify_token(parts[1])
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    if payload.get("role") not in ("user", "customer", "admin"):
        raise HTTPException(status_code=403, detail="Not a user token")

    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_current_admin(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> AdminUser:
    """Dependency to get current authenticated admin user.

    Accepts two token types:
    1. Legacy admin token (created by /admin/login) — looks up AdminUser table.
    2. Google OAuth token (created by /auth/google) with role='admin' — looks up
       User table. Returns a duck-typed object so callers get .id and .username.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = parts[1]
    try:
        payload = verify_token(token)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    role = payload.get("role", "")

    # --- Google OAuth admin: token has email claim, look up users table ---
    if payload.get("email") or role == "admin" and not payload.get("username"):
        google_user = db.query(User).filter(User.id == user_id).first()
        if google_user and google_user.role == "admin":
            # Return a minimal duck-typed wrapper so admin endpoints get .id / .username
            class _GoogleAdminProxy:
                def __init__(self, u):
                    self.id       = u.id
                    self.username = u.email
                    self.role     = "admin"
                    self.is_active= 1
            return _GoogleAdminProxy(google_user)

    # --- Legacy admin token: look up admin_users table ---
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Admin user not found or inactive")

    return user
