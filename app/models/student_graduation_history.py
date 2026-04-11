from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class StudentGraduationHistory(Base):
    """Immutable history of achieved graduations per student and modality."""

    __tablename__ = "student_graduation_history"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    modality_id = Column(
        Integer,
        ForeignKey("modalities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    graduation_id = Column(
        Integer,
        ForeignKey("graduations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    achieved_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    hours_when_achieved = Column(Numeric(10, 2), nullable=False)

    student = relationship("Student", back_populates="graduation_history")
    modality = relationship("Modality", back_populates="graduation_history_entries")
    graduation = relationship("Graduation", back_populates="history_entries")
