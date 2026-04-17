"""
AuditUserMiddleware — extracts the logged-in user from the JWT on every
request and stores it in the audit_user ContextVar.

get_db() reads that ContextVar and calls DBMS_SESSION.SET_IDENTIFIER so
Oracle triggers can record `changed_by` as the real app user (email /
username) rather than the generic DB schema user.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from utils.audit import audit_user
from utils.auth import verify_token


class AuditUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        username = "anonymous"

        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token_str = auth[7:]
            try:
                payload = verify_token(token_str)
                # Google OAuth tokens carry 'email'; legacy admin tokens carry 'username'
                username = (
                    payload.get("email")
                    or payload.get("username")
                    or f"user_{payload.get('user_id', '')}"
                )
            except Exception:
                pass  # invalid / expired token — leave as 'anonymous'

        token = audit_user.set(username)
        try:
            response = await call_next(request)
        finally:
            audit_user.reset(token)

        return response
