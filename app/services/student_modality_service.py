from __future__ import annotations

from decimal import Decimal
from typing import Any, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.models.graduation import Graduation
from app.models.modality import Modality
from app.models.student import Student
from app.models.student_modality import StudentModality
from app.models.user import User
from app.schemas.student import StudentModalityItem, StudentResponse
from app.services import training_service as training_svc


def load_student_with_modalities(db: Session, student_id: int) -> Optional[Student]:
    return (
        db.query(Student)
        .filter(Student.id == student_id)
        .options(
            selectinload(Student.student_modalities).selectinload(
                StudentModality.modality
            ),
            selectinload(Student.student_modalities).selectinload(
                StudentModality.graduation
            ),
        )
        .first()
    )


def assert_student_in_gym(db: Session, student_id: int, gym_id: int) -> Student:
    st = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.id == student_id, User.gym_id == gym_id)
        .first()
    )
    if not st:
        raise HTTPException(status_code=404, detail="Aluno não encontrado neste gym")
    return st


def add_student_modality(
    db: Session,
    gym_id: int,
    *,
    student_id: int,
    modality_id: int,
    graduation_id: int,
    hours_trained: Decimal = Decimal("0"),
) -> StudentModality:
    assert_student_in_gym(db, student_id, gym_id)

    dup = (
        db.query(StudentModality)
        .filter(
            StudentModality.student_id == student_id,
            StudentModality.modality_id == modality_id,
        )
        .first()
    )
    if dup:
        raise HTTPException(
            status_code=400,
            detail="Aluno já está inscrito nesta modalidade",
        )

    g = (
        db.query(Graduation)
        .filter(
            Graduation.id == graduation_id,
            Graduation.gym_id == gym_id,
            Graduation.modality_id == modality_id,
        )
        .first()
    )
    if not g:
        raise HTTPException(
            status_code=400,
            detail="Graduação inválida para esta modalidade e academia",
        )

    sm = StudentModality(
        student_id=student_id,
        modality_id=modality_id,
        graduation_id=graduation_id,
        hours_trained=hours_trained,
    )
    db.add(sm)
    db.flush()
    db.refresh(sm)
    return sm


def list_student_modalities_items(
    db: Session, gym_id: int, student_id: int
) -> List[StudentModalityItem]:
    assert_student_in_gym(db, student_id, gym_id)
    rows = (
        db.query(StudentModality)
        .join(Graduation, Graduation.id == StudentModality.graduation_id)
        .filter(
            StudentModality.student_id == student_id,
            Graduation.gym_id == gym_id,
        )
        .options(
            selectinload(StudentModality.modality),
            selectinload(StudentModality.graduation),
        )
        .all()
    )
    out: List[StudentModalityItem] = []
    for sm in rows:
        out.append(
            StudentModalityItem(
                id=sm.id,
                modality_id=sm.modality_id,
                modality_name=sm.modality.name,
                graduation_id=sm.graduation_id,
                graduation_name=sm.graduation.name,
                graduation_level=sm.graduation.level,
                hours_trained=sm.hours_trained,
            )
        )
    return out


def student_to_response(student: Student) -> StudentResponse:
    meds: List[StudentModalityItem] = []
    for sm in student.student_modalities:
        if sm.modality is None or sm.graduation is None:
            continue
        meds.append(
            StudentModalityItem(
                id=sm.id,
                modality_id=sm.modality_id,
                modality_name=sm.modality.name,
                graduation_id=sm.graduation_id,
                graduation_name=sm.graduation.name,
                graduation_level=sm.graduation.level,
                hours_trained=sm.hours_trained,
            )
        )
    base = StudentResponse.model_validate(student)
    return base.model_copy(update={"modalities": meds})


def ensure_default_enrollment(
    db: Session, gym_id: int, student_id: int
) -> None:
    """Muay Thai + primeira graduação (level 1) do gym, se existir."""
    if gym_id is None:
        return
    has_any = (
        db.query(StudentModality.id)
        .filter(StudentModality.student_id == student_id)
        .first()
    )
    if has_any:
        return

    m = db.query(Modality).filter(Modality.name == "Muay Thai").first()
    if not m:
        return

    g = (
        db.query(Graduation)
        .filter(
            Graduation.gym_id == gym_id,
            Graduation.modality_id == m.id,
            Graduation.level == 1,
        )
        .first()
    )
    if not g:
        return

    db.add(
        StudentModality(
            student_id=student_id,
            modality_id=m.id,
            graduation_id=g.id,
            hours_trained=Decimal("0"),
        )
    )


def get_next_graduation(db: Session, sm: StudentModality) -> Optional[Graduation]:
    return training_svc.get_next_graduation(db, sm)


def check_graduation_eligibility(sm: StudentModality) -> bool:
    return training_svc.check_graduation_eligibility(sm)


def eligibility_snapshot(db: Session, gym_id: int, student_id: int) -> List[dict[str, Any]]:
    """Por inscrição: próxima graduação e elegibilidade."""
    assert_student_in_gym(db, student_id, gym_id)
    rows = (
        db.query(StudentModality)
        .join(Graduation, Graduation.id == StudentModality.graduation_id)
        .filter(
            StudentModality.student_id == student_id,
            Graduation.gym_id == gym_id,
        )
        .options(selectinload(StudentModality.graduation))
        .all()
    )
    out = []
    for sm in rows:
        nxt = get_next_graduation(db, sm)
        out.append(
            {
                "student_modality_id": sm.id,
                "modality_id": sm.modality_id,
                "current_graduation_id": sm.graduation_id,
                "eligible_for_promotion": check_graduation_eligibility(sm),
                "next_graduation": (
                    {
                        "id": nxt.id,
                        "name": nxt.name,
                        "level": nxt.level,
                        "required_hours": float(nxt.required_hours),
                    }
                    if nxt
                    else None
                ),
            }
        )
    return out
