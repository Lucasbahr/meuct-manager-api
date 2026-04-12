from __future__ import annotations

from decimal import Decimal
from typing import Any, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.models.graduation import Graduation
from app.models.modality import Modality
from app.models.student import Student
from app.models.student_modality import StudentModality
from app.models.student_professor_modality import StudentProfessorModality
from app.models.user import User
from app.schemas.student import (
    ProfessorModalityItem,
    StudentModalityItem,
    StudentResponse,
)
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
            selectinload(Student.professor_modalities).selectinload(
                StudentProfessorModality.modality
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


def clear_student_professor_modalities(db: Session, student_id: int) -> None:
    db.query(StudentProfessorModality).filter(
        StudentProfessorModality.student_id == student_id
    ).delete(synchronize_session=False)


def set_student_professor_modalities(
    db: Session,
    gym_id: int,
    student_id: int,
    modality_ids: List[int],
) -> None:
    assert_student_in_gym(db, student_id, gym_id)
    seen: set[int] = set()
    clean_ids: List[int] = []
    for mid in modality_ids:
        if mid in seen:
            continue
        seen.add(mid)
        clean_ids.append(mid)
    for mid in clean_ids:
        m = db.query(Modality).filter(Modality.id == mid).first()
        if not m:
            raise HTTPException(status_code=400, detail="Modalidade inválida")
        has_graduation = (
            db.query(Graduation.id)
            .filter(Graduation.gym_id == gym_id, Graduation.modality_id == mid)
            .first()
        )
        if not has_graduation:
            raise HTTPException(
                status_code=400,
                detail="Modalidade indisponível nesta academia",
            )
    clear_student_professor_modalities(db, student_id)
    for mid in clean_ids:
        db.add(
            StudentProfessorModality(student_id=student_id, modality_id=mid)
        )


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
    prof_meds: List[ProfessorModalityItem] = []
    for pm in student.professor_modalities:
        if pm.modality is None:
            continue
        prof_meds.append(
            ProfessorModalityItem(
                id=pm.id,
                modality_id=pm.modality_id,
                modality_name=pm.modality.name,
            )
        )
    base = StudentResponse.model_validate(student)
    legacy_mod = meds[0].modality_name if meds else None
    legacy_grad = meds[0].graduation_name if meds else None
    return base.model_copy(
        update={
            "modalities": meds,
            "professor_modalities": prof_meds,
            "modalidade": legacy_mod,
            "graduacao": legacy_grad,
        }
    )


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
        .options(
            selectinload(StudentModality.graduation),
            selectinload(StudentModality.modality),
        )
        .all()
    )
    out = []
    for sm in rows:
        nxt = get_next_graduation(db, sm)
        out.append(
            {
                "student_modality_id": sm.id,
                "modality_id": sm.modality_id,
                "modality_name": sm.modality.name if sm.modality else None,
                "current_graduation_id": sm.graduation_id,
                "current_graduation_name": (
                    sm.graduation.name if sm.graduation else None
                ),
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
