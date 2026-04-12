from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", foreign_keys=[user_id])
    gym_id = Column(Integer, ForeignKey("gyms.id"), nullable=True, index=True)

    action = Column(String(64), nullable=False, index=True)
    target_type = Column(String(64), nullable=True)
    target_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, index=True)
