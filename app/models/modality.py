from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Modality(Base):
    """Global catalog of martial arts modalities."""

    __tablename__ = "modalities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)

    graduations = relationship(
        "Graduation", back_populates="modality", cascade="all, delete-orphan"
    )
    student_modalities = relationship(
        "StudentModality", back_populates="modality", cascade="all, delete-orphan"
    )
    graduation_history_entries = relationship(
        "StudentGraduationHistory",
        back_populates="modality",
    )
