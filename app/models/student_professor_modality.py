from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class StudentProfessorModality(Base):
    """
    Modalidades em que o aluno atua como professor (equipe de ensino).
    Distinto de StudentModality (inscrição como aluno + graduação).
    """

    __tablename__ = "student_professor_modalities"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "modality_id",
            name="uq_student_professor_mod_student_modality",
        ),
    )

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

    student = relationship("Student", back_populates="professor_modalities")
    modality = relationship("Modality", back_populates="student_professor_modalities")

    @property
    def modality_name(self) -> str:
        return self.modality.name if self.modality is not None else ""
