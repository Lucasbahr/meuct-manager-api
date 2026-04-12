from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_gym_id, require_staff
from app.core.roles import is_staff
from app.db.deps import get_db
from app.models.checkin import Checkin
from app.models.student import Student
from app.models.user import User
from app.schemas.response import ResponseBase
from app.services import training_service as training_svc
from app.services.audit_service import ACTION_CHECKIN, record_audit_event
from app.services import schedule_checkin_service as sch_chk

router = APIRouter(prefix="/checkin", tags=["Checkin"])


class CheckinCreateBody(BaseModel):
    """Check-in sempre vinculado a um horário da grade (`GymScheduleSlot`)."""

    schedule_slot_id: int = Field(ge=1)
    student_id: Optional[int] = Field(
        default=None,
        description="Somente equipe: check-in em nome do aluno",
    )


#  CHECK-IN
@router.post("/", response_model=ResponseBase)
def do_checkin(
    body: CheckinCreateBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    if body.student_id is not None:
        if not is_staff(user.get("role")):
            raise HTTPException(
                status_code=403,
                detail="Apenas equipe da academia pode informar student_id",
            )
        student = (
            db.query(Student)
            .join(User, User.id == Student.user_id)
            .filter(Student.id == body.student_id, User.gym_id == gym_id)
            .first()
        )
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        staff_mode = True
    else:
        student = db.query(Student).filter(Student.user_id == user["user_id"]).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        staff_mode = False

    slot, gym_class = sch_chk.load_active_slot(db, gym_id, body.schedule_slot_id)

    if not staff_mode:
        sch_chk.assert_self_checkin_time_window(slot)

    if sch_chk.has_checkin_for_slot_today(db, student.id, slot.id):
        raise HTTPException(
            status_code=400,
            detail="Check-in já realizado neste horário da grade hoje",
        )

    hours = sch_chk.slot_duration_hours(slot, gym_class)

    training = training_svc.add_training(
        db,
        student.id,
        gym_class.modality_id,
        hours,
        gym_id,
    )

    checkin = Checkin(
        student_id=student.id,
        gym_schedule_slot_id=slot.id,
        hours_credited=hours,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(checkin)

    record_audit_event(
        db,
        actor_user_id=user["user_id"],
        gym_id=gym_id,
        action=ACTION_CHECKIN,
        target_type="student",
        target_id=student.id,
        details={
            "student_user_id": student.user_id,
            "por_equipe": staff_mode,
            "schedule_slot_id": slot.id,
            "gym_class_id": gym_class.id,
            "modality_id": gym_class.modality_id,
            "hours_credited": str(hours),
        },
    )
    db.commit()

    return {
        "success": True,
        "message": "Check-in realizado com sucesso",
        "data": {
            "schedule_slot_id": slot.id,
            "hours_credited": float(hours),
            "modality_id": gym_class.modality_id,
            "training": training,
        },
    }


#  RESUMO
@router.get("/me/summary", response_model=ResponseBase)
def my_summary(user=Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.user_id == user["user_id"]).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    now = datetime.now(timezone.utc)
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_month = (
        db.query(Checkin)
        .filter(Checkin.student_id == student.id, Checkin.created_at >= start_month)
        .count()
    )

    total_all = db.query(Checkin).filter(Checkin.student_id == student.id).count()

    return {
        "success": True,
        "message": "Resumo de check-ins",
        "data": {"total_mes": total_month, "total_geral": total_all},
    }


#  HISTÓRICO
@router.get("/me/history", response_model=ResponseBase)
def my_history(user=Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.user_id == user["user_id"]).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    checkins = (
        db.query(
            func.date(Checkin.created_at).label("date"),
            func.count(Checkin.id).label("total"),
        )
        .filter(Checkin.student_id == student.id)
        .group_by(func.date(Checkin.created_at))
        .all()
    )

    return {
        "success": True,
        "message": "Histórico de check-ins",
        "data": [{"date": str(c.date), "total": c.total} for c in checkins],
    }


#  RANKING (ADMIN)
@router.get("/ranking", response_model=ResponseBase)
def ranking(
    user=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    results = (
        db.query(Student.nome, func.count(Checkin.id).label("total"))
        .join(User, User.id == Student.user_id)
        .join(Checkin, Checkin.student_id == Student.id)
        .filter(User.gym_id == gym_id)
        .group_by(Student.id)
        .order_by(func.count(Checkin.id).desc())
        .all()
    )

    return {
        "success": True,
        "message": "Ranking de alunos",
        "data": [{"nome": r.nome, "total": r.total} for r in results],
    }
