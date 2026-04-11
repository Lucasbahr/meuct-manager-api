"""Aulas e grade horária semanal por academia (tenant = gym)."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class GymClass(Base):
    """
    Definição de uma aula ofertada pela academia (ex.: Muay Thai iniciante).
    A grade (`GymScheduleSlot`) referencia esta entidade.
    """

    __tablename__ = "gym_classes"
    __table_args__ = (
        UniqueConstraint("gym_id", "name", name="uq_gym_classes_gym_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer,
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    modality_id = Column(
        Integer,
        ForeignKey("modalities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    instructor_name = Column(String(255), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    gym = relationship("Gym", back_populates="gym_classes")
    modality = relationship("Modality")
    schedule_slots = relationship(
        "GymScheduleSlot",
        back_populates="gym_class",
        cascade="all, delete-orphan",
    )


class GymScheduleSlot(Base):
    """Recorrência semanal: dia da semana + horário + aula."""

    __tablename__ = "gym_schedule_slots"
    __table_args__ = (
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_gym_schedule_weekday"),
        CheckConstraint("end_time > start_time", name="ck_gym_schedule_time_order"),
    )

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer,
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gym_class_id = Column(
        Integer,
        ForeignKey("gym_classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weekday = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room = Column(String(128), nullable=True)
    notes = Column(String(512), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    gym = relationship("Gym", back_populates="gym_schedule_slots")
    gym_class = relationship("GymClass", back_populates="schedule_slots")
