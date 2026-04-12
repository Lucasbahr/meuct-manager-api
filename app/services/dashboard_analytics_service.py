"""Agregações para painel da academia: alunos (MoM) e receita (loja + mensalidades)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Tuple

import pytz
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.user import User
from app.models.plan import Plan, StudentSubscription, SubscriptionPayment
from app.services import membership_service as mship
from app.services import sales_dashboard_service as sales_dash


def _utc_bounds_for_sp_month(year: int, month: int) -> Tuple[datetime, datetime]:
    """[start inclusive, end exclusive) em UTC para o mês civil em America/Sao_Paulo."""
    tz = pytz.timezone("America/Sao_Paulo")
    start_local = tz.localize(datetime(year, month, 1, 0, 0, 0))
    if month == 12:
        end_local = tz.localize(datetime(year + 1, 1, 1, 0, 0, 0))
    else:
        end_local = tz.localize(datetime(year, month + 1, 1, 0, 0, 0))
    return (
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
    )


def _previous_month(year: int, month: int) -> Tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _percent_change(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        if current == 0:
            return 0.0
        return None
    return round((current - previous) / previous * 100.0, 2)


def _student_counts_by_status(db: Session, gym_id: int) -> tuple[int, int, int]:
    total = (
        db.query(func.count(Student.id))
        .join(User, User.id == Student.user_id)
        .filter(User.gym_id == gym_id)
        .scalar()
        or 0
    )
    active = (
        db.query(func.count(Student.id))
        .join(User, User.id == Student.user_id)
        .filter(
            User.gym_id == gym_id,
            func.lower(func.coalesce(Student.status, "")) == "ativo",
        )
        .scalar()
        or 0
    )
    inactive = max(0, int(total) - int(active))
    return int(total), int(active), int(inactive)


def _new_students_in_range(
    db: Session, gym_id: int, start: datetime, end: datetime
) -> int:
    return (
        db.query(func.count(Student.id))
        .join(User, User.id == Student.user_id)
        .filter(
            User.gym_id == gym_id,
            Student.created_at >= start,
            Student.created_at < end,
        )
        .scalar()
        or 0
    )


def _membership_received_and_count(
    db: Session, gym_id: int, period_start: datetime, period_end: datetime
) -> tuple[Decimal, int]:
    mship.sync_membership_states(db, gym_id)
    total = (
        db.query(func.coalesce(func.sum(SubscriptionPayment.amount), 0))
        .join(StudentSubscription, StudentSubscription.id == SubscriptionPayment.subscription_id)
        .join(Plan, Plan.id == StudentSubscription.plan_id)
        .filter(
            Plan.gym_id == gym_id,
            SubscriptionPayment.status == "paid",
            SubscriptionPayment.paid_at.isnot(None),
            SubscriptionPayment.paid_at >= period_start,
            SubscriptionPayment.paid_at < period_end,
        )
        .scalar()
    )
    cnt = (
        db.query(func.count(SubscriptionPayment.id))
        .join(StudentSubscription, StudentSubscription.id == SubscriptionPayment.subscription_id)
        .join(Plan, Plan.id == StudentSubscription.plan_id)
        .filter(
            Plan.gym_id == gym_id,
            SubscriptionPayment.status == "paid",
            SubscriptionPayment.paid_at.isnot(None),
            SubscriptionPayment.paid_at >= period_start,
            SubscriptionPayment.paid_at < period_end,
        )
        .scalar()
        or 0
    )
    return Decimal(str(total or 0)), int(cnt)


def gym_dashboard_analytics(
    db: Session,
    gym_id: int,
    *,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict[str, Any]:
    tz = pytz.timezone("America/Sao_Paulo")
    now_sp = datetime.now(tz)
    y = year if year is not None else now_sp.year
    m = month if month is not None else now_sp.month
    if not (1 <= m <= 12):
        raise ValueError("month deve estar entre 1 e 12")

    cur_start, cur_end = _utc_bounds_for_sp_month(y, m)
    py, pm = _previous_month(y, m)
    prev_start, prev_end = _utc_bounds_for_sp_month(py, pm)

    total, active, inactive = _student_counts_by_status(db, gym_id)
    new_cur = _new_students_in_range(db, gym_id, cur_start, cur_end)
    new_prev = _new_students_in_range(db, gym_id, prev_start, prev_end)
    new_delta = new_cur - new_prev
    new_pct = _percent_change(float(new_cur), float(new_prev))

    prod_cur = sales_dash.gym_sales_dashboard(
        db, gym_id, period_start=cur_start, period_end=cur_end, top_limit=10
    )
    prod_prev = sales_dash.gym_sales_dashboard(
        db, gym_id, period_start=prev_start, period_end=prev_end, top_limit=10
    )
    prod_cur_total = float(prod_cur["total_sales"])
    prod_prev_total = float(prod_prev["total_sales"])
    prod_delta = prod_cur_total - prod_prev_total
    prod_pct = _percent_change(prod_cur_total, prod_prev_total)

    mem_cur_amt, mem_cur_cnt = _membership_received_and_count(db, gym_id, cur_start, cur_end)
    mem_prev_amt, mem_prev_cnt = _membership_received_and_count(
        db, gym_id, prev_start, prev_end
    )
    mem_cur_total = float(mem_cur_amt)
    mem_prev_total = float(mem_prev_amt)
    mem_delta = mem_cur_total - mem_prev_total
    mem_pct = _percent_change(mem_cur_total, mem_prev_total)

    mem_by_day = mship.revenue_by_day(db, gym_id, period_start=cur_start, period_end=cur_end)
    by_plan = mship.plans_performance_report(
        db, gym_id, period_start=cur_start, period_end=cur_end, sort_by="revenue_paid"
    )

    comb_cur = prod_cur_total + mem_cur_total
    comb_prev = prod_prev_total + mem_prev_total
    comb_delta = comb_cur - comb_prev
    comb_pct = _percent_change(comb_cur, comb_prev)

    return {
        "gym_id": gym_id,
        "timezone": "America/Sao_Paulo",
        "reference_year": y,
        "reference_month": m,
        "reference_period_start_utc": cur_start.isoformat(),
        "reference_period_end_exclusive_utc": cur_end.isoformat(),
        "previous_period_start_utc": prev_start.isoformat(),
        "previous_period_end_exclusive_utc": prev_end.isoformat(),
        "students": {
            "total": total,
            "active": active,
            "inactive": inactive,
            "new_in_reference_month": new_cur,
            "new_in_previous_month": new_prev,
            "new_delta_vs_previous_month": new_delta,
            "new_percent_change_vs_previous_month": new_pct,
        },
        "revenue": {
            "products": {
                "reference_month": {
                    "total": prod_cur_total,
                    "total_orders": int(prod_cur["total_orders"]),
                },
                "previous_month": {
                    "total": prod_prev_total,
                    "total_orders": int(prod_prev["total_orders"]),
                },
                "change_vs_previous_month": {
                    "amount_delta": round(prod_delta, 2),
                    "percent_change": prod_pct,
                },
                "sales_by_day": prod_cur.get("sales_by_day") or [],
            },
            "memberships": {
                "reference_month": {
                    "total": mem_cur_total,
                    "paid_payments_count": mem_cur_cnt,
                },
                "previous_month": {
                    "total": mem_prev_total,
                    "paid_payments_count": mem_prev_cnt,
                },
                "change_vs_previous_month": {
                    "amount_delta": round(mem_delta, 2),
                    "percent_change": mem_pct,
                },
                "revenue_by_day": [
                    {"date": str(r["day"]), "amount": float(r["amount"]), "count": r["count"]}
                    for r in mem_by_day
                ],
                "by_plan": [
                    {
                        "plan_id": r["plan_id"],
                        "plan_name": r["plan_name"],
                        "subscriptions_count": r["subscriptions_count"],
                        "revenue_paid": float(r["revenue_paid"]),
                    }
                    for r in by_plan
                ],
            },
            "combined": {
                "reference_month_total": round(comb_cur, 2),
                "previous_month_total": round(comb_prev, 2),
                "change_vs_previous_month": {
                    "amount_delta": round(comb_delta, 2),
                    "percent_change": comb_pct,
                },
            },
        },
    }
