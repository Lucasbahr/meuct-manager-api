from datetime import date, datetime, timedelta, timezone

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_gym_id, require_staff
from app.db.deps import get_db
from app.models.audit_event import AuditEvent
from app.models.checkin import Checkin
from app.models.student import Student
from app.models.user import User
from app.schemas.response import ResponseBase
from app.schemas.sales_dashboard import GymSalesDashboardOut
from app.services import sales_dashboard_service as sales_dash

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _iso(dt):
    return dt.isoformat() if dt else None


def _serialize_audit(ev: AuditEvent, include_actor_email: bool = False) -> dict:
    row = {
        "id": ev.id,
        "actor_user_id": ev.user_id,
        "gym_id": ev.gym_id,
        "action": ev.action,
        "target_type": ev.target_type,
        "target_id": ev.target_id,
        "details": ev.details,
        "created_at": _iso(ev.created_at),
    }
    if include_actor_email and ev.user:
        row["actor_email"] = ev.user.email
    return row


@router.get("/me", response_model=ResponseBase)
def dashboard_me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user["user_id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    student = db.query(Student).filter(Student.user_id == db_user.id).first()
    now = datetime.now(timezone.utc)
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    checkins = None
    if student:
        total_month = (
            db.query(Checkin)
            .filter(Checkin.student_id == student.id, Checkin.created_at >= start_month)
            .count()
        )
        total_all = db.query(Checkin).filter(Checkin.student_id == student.id).count()
        checkins = {
            "total_mes": total_month,
            "total_geral": total_all,
        }

    recent = (
        db.query(AuditEvent)
        .filter(AuditEvent.user_id == db_user.id)
        .order_by(AuditEvent.created_at.desc())
        .limit(40)
        .all()
    )

    return {
        "success": True,
        "message": "Painel do usuário",
        "data": {
            "usuario": {
                "id": db_user.id,
                "email": db_user.email,
                "role": db_user.role,
                "gym_id": db_user.gym_id,
                "ultimo_login_em": _iso(db_user.last_login_at),
            },
            "checkins": checkins,
            "minhas_acoes_recentes": [_serialize_audit(e) for e in recent],
        },
    }


@router.get("/academy", response_model=ResponseBase)
def dashboard_academy(
    user=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
    audit_limit: int = Query(80, ge=1, le=200),
    logins_limit: int = Query(30, ge=1, le=100),
):
    tz = pytz.timezone("America/Sao_Paulo")
    today_start = datetime.now(tz).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_cutoff_utc = datetime.now(timezone.utc) - timedelta(days=7)

    alunos_ativos = (
        db.query(func.count(Student.id))
        .join(User, User.id == Student.user_id)
        .filter(User.gym_id == gym_id, Student.status == "ativo")
        .scalar()
    )

    checkins_hoje = (
        db.query(func.count(Checkin.id))
        .join(Student, Student.id == Checkin.student_id)
        .join(User, User.id == Student.user_id)
        .filter(User.gym_id == gym_id, Checkin.created_at >= today_start)
        .scalar()
    )

    checkins_7d = (
        db.query(func.count(Checkin.id))
        .join(Student, Student.id == Checkin.student_id)
        .join(User, User.id == Student.user_id)
        .filter(User.gym_id == gym_id, Checkin.created_at >= week_cutoff_utc)
        .scalar()
    )

    audit_rows = (
        db.query(AuditEvent)
        .options(joinedload(AuditEvent.user))
        .filter(AuditEvent.gym_id == gym_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(audit_limit)
        .all()
    )

    logins_rows = (
        db.query(User)
        .filter(User.gym_id == gym_id)
        .order_by(User.last_login_at.desc())
        .limit(logins_limit)
        .all()
    )

    return {
        "success": True,
        "message": "Painel do gym",
        "data": {
            "gym_id": gym_id,
            "resumo": {
                "alunos_ativos": alunos_ativos or 0,
                "checkins_hoje": checkins_hoje or 0,
                "checkins_ultimos_7_dias": checkins_7d or 0,
            },
            "ultimos_logins": [
                {
                    "email": u.email,
                    "role": u.role,
                    "ultimo_login_em": _iso(u.last_login_at),
                }
                for u in logins_rows
            ],
            "auditoria": [
                _serialize_audit(e, include_actor_email=True) for e in audit_rows
            ],
        },
    }


@router.get("/sales", response_model=ResponseBase)
def dashboard_sales(
    _staff=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
    days: int | None = Query(None, description="7 ou 30 (alternativa a date_from/date_to)"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    top_products_limit: int = Query(10, ge=1, le=50),
):
    if days is not None and days not in (7, 30):
        raise HTTPException(
            status_code=400, detail="days deve ser 7 ou 30, ou use date_from e date_to"
        )
    if (date_from is None) != (date_to is None):
        raise HTTPException(
            status_code=400, detail="Informe date_from e date_to juntos"
        )
    start, end = sales_dash.resolve_period(
        days=days, date_from=date_from, date_to=date_to
    )
    data = sales_dash.gym_sales_dashboard(
        db,
        gym_id,
        period_start=start,
        period_end=end,
        top_limit=top_products_limit,
    )
    return {
        "success": True,
        "message": "Vendas da academia",
        "data": GymSalesDashboardOut.model_validate(data).model_dump(),
    }
