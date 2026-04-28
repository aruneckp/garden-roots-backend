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
    1. Google OAuth token (has 'email' claim, no 'username') — looks up users table.
    2. Legacy admin token (has 'username' claim, no 'email') — looks up admin_users table.

    Both must carry role='admin' in the JWT (signed by our SECRET_KEY).
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

    # --- Google OAuth token: identified by presence of 'email' claim ---
    if payload.get("email"):
        if role != "admin":
            raise HTTPException(status_code=403, detail="Not an admin token")
        google_user = db.query(User).filter(User.id == user_id).first()
        if not google_user:
            raise HTTPException(status_code=401, detail="User not found")

        class _GoogleAdminProxy:
            def __init__(self, u):
                self.id        = u.id
                self.username  = u.email
                self.full_name = getattr(u, 'name', None) or u.email
                self.email     = u.email
                self.role      = "admin"
                self.is_active = 1

        return _GoogleAdminProxy(google_user)

    # --- Legacy admin token: identified by presence of 'username' claim ---
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Admin user not found or inactive")

    return user


async def get_optional_admin(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Optional admin dependency — returns the admin object if a valid admin token is present,
    or None if no/invalid token is provided. Used on public endpoints that may be called by admins."""
    if not authorization:
        return None
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        payload = verify_token(parts[1])
        if payload.get("role") != "admin":
            return None
        user_id = payload.get("user_id")
        if not user_id:
            return None
        # Google OAuth admin
        if payload.get("email"):
            google_user = db.query(User).filter(User.id == user_id).first()
            if not google_user:
                return None

            class _GoogleAdminProxy:
                def __init__(self, u):
                    self.id        = u.id
                    self.username  = u.email
                    self.full_name = getattr(u, 'name', None) or u.email
                    self.email     = u.email
                    self.role      = "admin"
                    self.is_active = 1

            return _GoogleAdminProxy(google_user)
        # Legacy admin
        user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        return None
