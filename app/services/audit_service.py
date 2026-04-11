from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent

ACTION_LOGIN = "LOGIN"
ACTION_CHECKIN = "CHECKIN"
ACTION_USER_ROLE_CHANGED = "USER_ROLE_CHANGED"
ACTION_USER_DELETED = "USER_DELETED"
ACTION_PASSWORD_CHANGED = "PASSWORD_CHANGED"


def record_audit_event(
    db: Session,
    *,
    actor_user_id: int,
    gym_id: Optional[int],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    ev = AuditEvent(
        user_id=actor_user_id,
        gym_id=gym_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    )
    db.add(ev)
    return ev
