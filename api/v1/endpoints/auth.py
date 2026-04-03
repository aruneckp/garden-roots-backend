"""
Customer authentication via Google OAuth.
Flow:
  1. Frontend obtains a Google ID token (via Google Identity Services).
  2. POST /auth/google with { id_token: "..." } — we verify with Google, create/find user.
  3. We return our own JWT so the frontend can call protected /users/* endpoints.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from config.settings import settings
from database.connection import get_db
from database.models import User
from utils.auth import create_user_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleTokenIn(BaseModel):
    id_token: str



class UserOut(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    phone: Optional[str] = None
    role: str = "customer"

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    token: str
    user: UserOut
    is_new_user: bool
    needs_phone: bool


@router.post("/google", response_model=AuthResponse)
def google_login(payload: GoogleTokenIn, db: Session = Depends(get_db)):
    """Verify Google ID token, create or find user, return our JWT."""
    try:
        id_info = id_token.verify_oauth2_token(
            payload.id_token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_id = id_info.get("sub")
    email = id_info.get("email", "")
    name = id_info.get("name")
    picture = id_info.get("picture")

    if not google_id:
        raise HTTPException(status_code=400, detail="Google token missing sub claim")

    # Find existing user by google_id or email
    user = db.query(User).filter(User.google_id == google_id).first()
    is_new_user = False

    if not user:
        # Check if email already registered (edge case: re-linked account)
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_id = google_id
            user.picture = picture
        else:
            user = User(
                google_id=google_id,
                email=email,
                name=name,
                picture=picture,
            )
            db.add(user)
            is_new_user = True

    db.commit()
    db.refresh(user)

    token = create_user_token(user.id, user.email, user.role or "customer")
    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
        is_new_user=is_new_user,
        needs_phone=not bool(user.phone),
    )


