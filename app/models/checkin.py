from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric
from datetime import datetime
from sqlalchemy.orm import relationship

from app.db.session import Base


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    gym_schedule_slot_id = Column(
        Integer,
        ForeignKey("gym_schedule_slots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    hours_credited = Column(Numeric(10, 2), nullable=True)

    schedule_slot = relationship("GymScheduleSlot", back_populates="checkins")
