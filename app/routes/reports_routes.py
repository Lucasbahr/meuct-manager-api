from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_gym_id, require_staff
from app.db.deps import get_db
from app.schemas.membership import (
    FinancialReportOut,
    PlanSalesRow,
    RevenueDayRow,
    StudentsReportOut,
)
from app.schemas.response import ResponseBase
from app.services import membership_service as membership_svc

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/financial", response_model=ResponseBase)
def report_financial(
    days: Optional[int] = Query(None, description="7, 30, 90 ou 365 se sem date_from/date_to"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    _staff=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    start, end = membership_svc.resolve_report_period(
        days=days, date_from=date_from, date_to=date_to
    )
    data = membership_svc.financial_report(db, gym_id, period_start=start, period_end=end)
    return {
        "success": True,
        "message": "Relatório financeiro (mensalidades)",
        "data": FinancialReportOut(**data).model_dump(),
    }


@router.get("/students", response_model=ResponseBase)
def report_students(
    _staff=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    data = membership_svc.students_report(db, gym_id)
    return {
        "success": True,
        "message": "Relatório de alunos por status de assinatura",
        "data": StudentsReportOut(**data).model_dump(),
    }


@router.get("/revenue", response_model=ResponseBase)
def report_revenue(
    days: Optional[int] = Query(None),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    _staff=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    start, end = membership_svc.resolve_report_period(
        days=days, date_from=date_from, date_to=date_to
    )
    rows = membership_svc.revenue_by_day(db, gym_id, period_start=start, period_end=end)
    return {
        "success": True,
        "message": "Receita de mensalidades por dia (somente pagamentos pagos)",
        "data": [RevenueDayRow(**r).model_dump() for r in rows],
    }


@router.get("/plans", response_model=ResponseBase)
def report_plans(
    days: Optional[int] = Query(None),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: Literal["subscriptions_count", "revenue_paid"] = Query("subscriptions_count"),
    _staff=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    start, end = membership_svc.resolve_report_period(
        days=days, date_from=date_from, date_to=date_to
    )
    rows = membership_svc.plans_performance_report(
        db,
        gym_id,
        period_start=start,
        period_end=end,
        sort_by=sort_by,
    )
    return {
        "success": True,
        "message": "Desempenho dos planos",
        "data": [PlanSalesRow(**r).model_dump() for r in rows],
    }
