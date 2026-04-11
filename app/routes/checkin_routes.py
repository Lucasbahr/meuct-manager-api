from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import pytz
from sqlalchemy import func
from typing import Optional

from app.schemas.response import ResponseBase
from app.db.deps import get_db
from app.core.deps import get_current_user, require_staff, require_gym_id
from app.core.roles import is_staff
from app.models.student import Student
from app.models.checkin import Checkin
from app.models.user import User
from app.services.audit_service import record_audit_event, ACTION_CHECKIN

router = APIRouter(prefix="/checkin", tags=["Checkin"])


#  CHECK-IN
@router.post("/", response_model=ResponseBase)
def do_checkin(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    student_id: Optional[int] = Body(default=None, embed=True),
    gym_id: int = Depends(require_gym_id),
):
    if student_id is not None:
        if not is_staff(user.get("role")):
            raise HTTPException(
                status_code=403,
                detail="Apenas equipe da academia pode informar student_id",
            )
        student = (
            db.query(Student)
            .join(User, User.id == Student.user_id)
            .filter(Student.id == student_id, User.gym_id == gym_id)
            .first()
        )
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
    else:
        student = db.query(Student).filter(Student.user_id == user["user_id"]).first()

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

    tz = pytz.timezone("America/Sao_Paulo")
    today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

    existing = (
        db.query(Checkin)
        .filter(Checkin.student_id == student.id, Checkin.created_at >= today_start)
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Check-in já realizado hoje")

    checkin = Checkin(student_id=student.id)

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
            "por_equipe": student_id is not None,
        },
    )
    db.commit()

    return {"success": True, "message": "Check-in realizado com sucesso", "data": None}


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
