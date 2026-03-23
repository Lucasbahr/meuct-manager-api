from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import pytz
from sqlalchemy import func

from app.schemas.response import ResponseBase
from app.db.deps import get_db
from app.core.deps import get_current_user, require_admin
from app.models.student import Student
from app.models.checkin import Checkin

router = APIRouter(prefix="/checkin", tags=["Checkin"])


#  CHECK-IN
@router.post("/", response_model=ResponseBase)
def do_checkin(user=Depends(get_current_user), db: Session = Depends(get_db)):
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
def ranking(user=Depends(require_admin), db: Session = Depends(get_db)):
    results = (
        db.query(Student.nome, func.count(Checkin.id).label("total"))
        .join(Checkin, Checkin.student_id == Student.id)
        .group_by(Student.id)
        .order_by(func.count(Checkin.id).desc())
        .all()
    )

    return {
        "success": True,
        "message": "Ranking de alunos",
        "data": [{"nome": r.nome, "total": r.total} for r in results],
    }
