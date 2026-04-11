from sqlalchemy import Column, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class StudentModality(Base):
    """
    Student enrollment in a modality: current graduation and accumulated hours.
    Unique (student_id, modality_id).
    """

    __tablename__ = "student_modalities"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "modality_id",
            name="uq_student_modalities_student_modality",
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
    graduation_id = Column(
        Integer,
        ForeignKey("graduations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    hours_trained = Column(Numeric(10, 2), nullable=False, default=0)

    student = relationship("Student", back_populates="student_modalities")
    modality = relationship("Modality", back_populates="student_modalities")
    graduation = relationship("Graduation", back_populates="student_modalities")
