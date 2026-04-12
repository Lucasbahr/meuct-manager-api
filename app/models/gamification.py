from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class StudentStats(Base):
    """Aggregated gamification state per student (one row per student)."""

    __tablename__ = "student_stats"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    total_xp = Column(Integer, nullable=False, default=0)
    level = Column(Integer, nullable=False, default=0)
    current_streak = Column(Integer, nullable=False, default=0)
    best_streak = Column(Integer, nullable=False, default=0)
    last_training_date = Column(Date, nullable=True)
    training_sessions_count = Column(Integer, nullable=False, default=0)

    student = relationship("Student", back_populates="stats")


class XpLog(Base):
    __tablename__ = "xp_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(Integer, nullable=False)
    source = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)

    student = relationship("Student", back_populates="xp_logs")


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(128), nullable=True)

    student_unlocks = relationship(
        "StudentBadge", back_populates="badge", cascade="all, delete-orphan"
    )


class StudentBadge(Base):
    __tablename__ = "student_badges"
    __table_args__ = (
        UniqueConstraint("student_id", "badge_id", name="uq_student_badges_student_badge"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    badge_id = Column(
        Integer,
        ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unlocked_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)

    student = relationship("Student", back_populates="student_badges")
    badge = relationship("Badge", back_populates="student_unlocks")
