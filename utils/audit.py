"""
Audit user context variable.

The AuditUserMiddleware (middleware/audit_middleware.py) extracts the
logged-in user from the request's JWT and stores it here.
get_db() then reads it and passes it to Oracle via DBMS_SESSION.SET_IDENTIFIER,
so that every audit trigger can record who made the change.
"""
from contextvars import ContextVar

# Default 'anonymous' covers unauthenticated / public endpoints
audit_user: ContextVar[str] = ContextVar('audit_user', default='anonymous')
