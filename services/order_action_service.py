import json
from sqlalchemy.orm import Session
from database.models import AdminUser, OrderActionLog, OrderActionType


def log_order_action(db: Session, order_id: int, action_type_code: str, actor=None, details=None, note=None):
    """Insert one row into order_action_logs. Silently skips if the action type code is unknown."""
    atype = (
        db.query(OrderActionType)
        .filter(OrderActionType.code == action_type_code, OrderActionType.is_active == 1)
        .first()
    )
    if not atype:
        return
    db.add(OrderActionLog(
        order_id=order_id,
        action_type_id=atype.id,
        performed_by=getattr(actor, "username", None) or "system",
        performed_by_admin_id=actor.id if isinstance(actor, AdminUser) else None,
        details=json.dumps(details) if details is not None else None,
        note=note,
    ))
