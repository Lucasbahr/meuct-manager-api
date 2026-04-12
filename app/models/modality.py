from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class Modality(Base):
    """Catálogo global de modalidades."""

    __tablename__ = "modalities"
    __table_args__ = (UniqueConstraint("name", name="uq_modalities_name"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)

    graduations = relationship(
        "Graduation", back_populates="modality", cascade="all, delete-orphan"
    )
    student_modalities = relationship(
        "StudentModality", back_populates="modality", cascade="all, delete-orphan"
    )
    student_professor_modalities = relationship(
        "StudentProfessorModality",
        back_populates="modality",
        cascade="all, delete-orphan",
    )
    graduation_history_entries = relationship(
        "StudentGraduationHistory",
        back_populates="modality",
    )
