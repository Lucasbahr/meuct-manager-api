from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class Graduation(Base):
    """
    Belt/rank step per academy and modality (tenant).
    `level` is ordering; `required_hours` to become eligible for promotion exam.
    """

    __tablename__ = "graduations"
    __table_args__ = (
        UniqueConstraint(
            "gym_id",
            "modality_id",
            "level",
            name="uq_graduations_gym_modality_level",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer,
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    modality_id = Column(
        Integer,
        ForeignKey("modalities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(128), nullable=False)
    level = Column(Integer, nullable=False)
    required_hours = Column(Numeric(10, 2), nullable=False)

    gym = relationship("Gym", back_populates="graduations")
    modality = relationship("Modality", back_populates="graduations")
    student_modalities = relationship(
        "StudentModality", back_populates="graduation"
    )
    history_entries = relationship(
        "StudentGraduationHistory",
        back_populates="graduation",
    )
