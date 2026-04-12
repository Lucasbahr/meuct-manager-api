from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.plan import Plan, StudentSubscription, SubscriptionPayment
from app.models.student import Student
from app.models.user import User


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _plan_price_is_free(price: Any) -> bool:
    """Preço zero = plano gratuito (valor efetivo 0, independente do tipo vindo do DB)."""
    if price is None:
        return False
    try:
        return Decimal(str(price)) == 0
    except Exception:
        return False


def resolve_report_period(
    *,
    days: Optional[int],
    date_from: Optional[date],
    date_to: Optional[date],
) -> Tuple[datetime, datetime]:
    """Intervalo [start inclusive, end exclusive) em UTC."""
    now = datetime.now(timezone.utc)
    if date_from is not None and date_to is not None:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        end = datetime.combine(date_to, time.min, tzinfo=timezone.utc) + timedelta(days=1)
        return start, end
    d = days if days in (7, 30, 90, 365) else 30
    end = now
    start = end - timedelta(days=d)
    return start, end


def sync_membership_states(db: Session, gym_id: int) -> None:
    """Marca pagamentos vencidos e alinha status das assinaturas."""
    today = _utc_today()
    overdue_payments = (
        db.query(SubscriptionPayment)
        .join(StudentSubscription, StudentSubscription.id == SubscriptionPayment.subscription_id)
        .join(Plan, Plan.id == StudentSubscription.plan_id)
        .filter(
            Plan.gym_id == gym_id,
            SubscriptionPayment.status == "pending",
            SubscriptionPayment.due_date < today,
        )
        .all()
    )
    for p in overdue_payments:
        p.status = "overdue"

    subs = (
        db.query(StudentSubscription)
        .join(Plan, Plan.id == StudentSubscription.plan_id)
        .filter(Plan.gym_id == gym_id, StudentSubscription.status != "canceled")
        .all()
    )
    for sub in subs:
        has_overdue_payment = (
            db.query(SubscriptionPayment.id)
            .filter(
                SubscriptionPayment.subscription_id == sub.id,
                SubscriptionPayment.status == "overdue",
            )
            .first()
        )
        if has_overdue_payment or sub.end_date < today:
            sub.status = "overdue"
        else:
            sub.status = "active"

    db.commit()


def create_plan(
    db: Session,
    gym_id: int,
    *,
    name: str,
    price: Decimal,
    duration_days: int,
    is_active: bool = True,
) -> Plan:
    plan = Plan(
        gym_id=gym_id,
        name=name.strip(),
        price=price,
        duration_days=duration_days,
        is_active=is_active,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def list_plans(db: Session, gym_id: int, active_only: bool = False) -> List[Plan]:
    q = db.query(Plan).filter(Plan.gym_id == gym_id)
    if active_only:
        q = q.filter(Plan.is_active.is_(True))
    return q.order_by(Plan.name.asc()).all()


def get_plan_for_gym(db: Session, gym_id: int, plan_id: int) -> Optional[Plan]:
    return (
        db.query(Plan)
        .filter(Plan.id == plan_id, Plan.gym_id == gym_id)
        .first()
    )


def _student_in_gym(db: Session, student_id: int, gym_id: int) -> Optional[Student]:
    return (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.id == student_id, User.gym_id == gym_id)
        .first()
    )


def _open_subscription(db: Session, student_id: int) -> Optional[StudentSubscription]:
    return (
        db.query(StudentSubscription)
        .filter(
            StudentSubscription.student_id == student_id,
            StudentSubscription.status.in_(("active", "overdue")),
        )
        .first()
    )


def create_subscription(
    db: Session,
    gym_id: int,
    *,
    student_id: int,
    plan_id: int,
    start_date: Optional[date] = None,
) -> Tuple[StudentSubscription, SubscriptionPayment]:
    plan = get_plan_for_gym(db, gym_id, plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plano não encontrado ou inativo")

    student = _student_in_gym(db, student_id, gym_id)
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado neste gym")

    if _open_subscription(db, student_id):
        raise HTTPException(
            status_code=400,
            detail="Aluno já possui assinatura ativa ou em atraso",
        )

    start = start_date or _utc_today()
    duration = int(plan.duration_days)
    end = start + timedelta(days=duration)

    sub = StudentSubscription(
        student_id=student_id,
        plan_id=plan_id,
        start_date=start,
        end_date=end,
        status="active",
    )
    db.add(sub)
    db.flush()

    is_free = _plan_price_is_free(plan.price)
    now = datetime.now(timezone.utc)
    payment = SubscriptionPayment(
        student_id=student_id,
        subscription_id=sub.id,
        amount=plan.price,
        status="paid" if is_free else "pending",
        due_date=start,
        paid_at=now if is_free else None,
    )
    db.add(payment)
    db.commit()
    db.refresh(sub)
    db.refresh(payment)
    return sub, payment


def mark_payment_paid(db: Session, gym_id: int, payment_id: int) -> SubscriptionPayment:
    payment = (
        db.query(SubscriptionPayment)
        .join(StudentSubscription, StudentSubscription.id == SubscriptionPayment.subscription_id)
        .join(Plan, Plan.id == StudentSubscription.plan_id)
        .filter(SubscriptionPayment.id == payment_id, Plan.gym_id == gym_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    if payment.status == "paid":
        raise HTTPException(status_code=400, detail="Pagamento já registrado como pago")

    sub = payment.subscription
    plan = sub.plan

    other_paid = (
        db.query(func.count(SubscriptionPayment.id))
        .filter(
            SubscriptionPayment.subscription_id == sub.id,
            SubscriptionPayment.status == "paid",
            SubscriptionPayment.id != payment.id,
        )
        .scalar()
        or 0
    )

    now = datetime.now(timezone.utc)
    payment.status = "paid"
    payment.paid_at = now

    if other_paid > 0:
        sub.end_date = sub.end_date + timedelta(days=int(plan.duration_days))

    sub.status = "active"
    db.commit()
    db.refresh(payment)
    return payment


def build_students_alerts(db: Session, gym_id: int) -> dict[str, Any]:
    sync_membership_states(db, gym_id)
    today = _utc_today()
    horizon = today + timedelta(days=3)

    base_join = (
        db.query(SubscriptionPayment, StudentSubscription, Plan, Student)
        .join(StudentSubscription, StudentSubscription.id == SubscriptionPayment.subscription_id)
        .join(Plan, Plan.id == StudentSubscription.plan_id)
        .join(Student, Student.id == SubscriptionPayment.student_id)
        .filter(Plan.gym_id == gym_id)
    )

    due_soon_rows = (
        base_join.filter(
            SubscriptionPayment.status == "pending",
            SubscriptionPayment.due_date >= today,
            SubscriptionPayment.due_date <= horizon,
        )
        .order_by(SubscriptionPayment.due_date.asc())
        .all()
    )

    due_soon = []
    for pay, sub, plan, st in due_soon_rows:
        due_soon.append(
            {
                "student_id": st.id,
                "student_name": st.nome,
                "subscription_id": sub.id,
                "plan_id": plan.id,
                "plan_name": plan.name,
                "payment_id": pay.id,
                "amount": pay.amount,
                "due_date": pay.due_date,
                "subscription_status": sub.status,
                "reason": "pagamento_vence_em_ate_3_dias",
            }
        )

    overdue_pay_rows = (
        base_join.filter(SubscriptionPayment.status == "overdue")
        .order_by(SubscriptionPayment.due_date.asc())
        .all()
    )

    overdue: List[dict[str, Any]] = []
    for pay, sub, plan, st in overdue_pay_rows:
        overdue.append(
            {
                "student_id": st.id,
                "student_name": st.nome,
                "subscription_id": sub.id,
                "plan_id": plan.id,
                "plan_name": plan.name,
                "payment_id": pay.id,
                "amount": pay.amount,
                "due_date": pay.due_date,
                "subscription_status": sub.status,
                "reason": "pagamento_atrasado",
            }
        )

    overdue_sub_rows = (
        db.query(StudentSubscription, Plan, Student)
        .join(Plan, Plan.id == StudentSubscription.plan_id)
        .join(Student, Student.id == StudentSubscription.student_id)
        .filter(
            Plan.gym_id == gym_id,
            StudentSubscription.status == "overdue",
        )
        .all()
    )

    for sub, plan, st in overdue_sub_rows:
        if any(x["subscription_id"] == sub.id for x in overdue):
            continue
        overdue.append(
            {
                "student_id": st.id,
                "student_name": st.nome,
                "subscription_id": sub.id,
                "plan_id": plan.id,
                "plan_name": plan.name,
                "payment_id": None,
                "amount": None,
                "due_date": sub.end_date,
                "subscription_status": sub.status,
                "reason": "assinatura_em_atraso",
            }
        )

    return {"due_soon": due_soon, "overdue": overdue}


def _payments_in_gym_query(db: Session, gym_id: int):
    return (
        db.query(SubscriptionPayment)
        .join(StudentSubscription, StudentSubscription.id == SubscriptionPayment.subscription_id)
        .join(Plan, Plan.id == StudentSubscription.plan_id)
        .filter(Plan.gym_id == gym_id)
    )


def financial_report(
    db: Session,
    gym_id: int,
    *,
    period_start: datetime,
    period_end: datetime,
) -> dict[str, Any]:
    sync_membership_states(db, gym_id)
    qbase = _payments_in_gym_query(db, gym_id).filter(
        SubscriptionPayment.created_at >= period_start,
        SubscriptionPayment.created_at < period_end,
    )

    total_payments = qbase.count()

    total_received = (
        _payments_in_gym_query(db, gym_id)
        .filter(
            SubscriptionPayment.status == "paid",
            SubscriptionPayment.paid_at.isnot(None),
            SubscriptionPayment.paid_at >= period_start,
            SubscriptionPayment.paid_at < period_end,
        )
        .with_entities(func.coalesce(func.sum(SubscriptionPayment.amount), 0))
        .scalar()
    )

    total_pending = (
        qbase.filter(SubscriptionPayment.status == "pending")
        .with_entities(func.coalesce(func.sum(SubscriptionPayment.amount), 0))
        .scalar()
    )

    total_overdue = (
        qbase.filter(SubscriptionPayment.status == "overdue")
        .with_entities(func.coalesce(func.sum(SubscriptionPayment.amount), 0))
        .scalar()
    )

    return {
        "total_received": Decimal(str(total_received or 0)),
        "total_pending": Decimal(str(total_pending or 0)),
        "total_overdue": Decimal(str(total_overdue or 0)),
        "total_payments": int(total_payments),
    }


def students_report(db: Session, gym_id: int) -> dict[str, int]:
    sync_membership_states(db, gym_id)
    total_students = (
        db.query(func.count(Student.id))
        .join(User, User.id == Student.user_id)
        .filter(User.gym_id == gym_id)
        .scalar()
        or 0
    )

    q = (
        db.query(StudentSubscription.status, func.count(StudentSubscription.id))
        .join(Plan, Plan.id == StudentSubscription.plan_id)
        .filter(Plan.gym_id == gym_id)
        .group_by(StudentSubscription.status)
    )
    by_status = {row[0]: row[1] for row in q.all()}

    return {
        "total_students": int(total_students),
        "active_students": int(by_status.get("active", 0)),
        "overdue_students": int(by_status.get("overdue", 0)),
        "canceled_students": int(by_status.get("canceled", 0)),
    }


def _revenue_day_col(paid_at_col, dialect_name: str):
    if dialect_name == "sqlite":
        return func.strftime("%Y-%m-%d", paid_at_col)
    return func.to_char(paid_at_col, "YYYY-MM-DD")


def revenue_by_day(
    db: Session,
    gym_id: int,
    *,
    period_start: datetime,
    period_end: datetime,
) -> List[dict[str, Any]]:
    sync_membership_states(db, gym_id)
    dialect_name = db.get_bind().dialect.name
    day_col = _revenue_day_col(SubscriptionPayment.paid_at, dialect_name)
    rows = (
        db.query(
            day_col.label("d"),
            func.coalesce(func.sum(SubscriptionPayment.amount), 0).label("amount"),
            func.count(SubscriptionPayment.id).label("cnt"),
        )
        .join(StudentSubscription, StudentSubscription.id == SubscriptionPayment.subscription_id)
        .join(Plan, Plan.id == StudentSubscription.plan_id)
        .filter(
            Plan.gym_id == gym_id,
            SubscriptionPayment.status == "paid",
            SubscriptionPayment.paid_at.isnot(None),
            SubscriptionPayment.paid_at >= period_start,
            SubscriptionPayment.paid_at < period_end,
        )
        .group_by(day_col)
        .order_by(day_col.asc())
        .all()
    )
    return [
        {"day": r.d, "amount": Decimal(str(r.amount or 0)), "count": int(r.cnt)}
        for r in rows
    ]


def plans_performance_report(
    db: Session,
    gym_id: int,
    *,
    period_start: datetime,
    period_end: datetime,
    sort_by: str = "subscriptions_count",
) -> List[dict[str, Any]]:
    """
    sort_by: subscriptions_count | revenue_paid
    """
    sync_membership_states(db, gym_id)

    sub_counts = (
        db.query(
            Plan.id.label("plan_id"),
            Plan.name.label("plan_name"),
            func.count(StudentSubscription.id).label("subscriptions_count"),
        )
        .select_from(Plan)
        .outerjoin(
            StudentSubscription,
            and_(
                StudentSubscription.plan_id == Plan.id,
                StudentSubscription.created_at >= period_start,
                StudentSubscription.created_at < period_end,
            ),
        )
        .filter(Plan.gym_id == gym_id)
        .group_by(Plan.id, Plan.name)
        .subquery()
    )

    revenue = (
        db.query(
            Plan.id.label("plan_id"),
            func.coalesce(func.sum(SubscriptionPayment.amount), 0).label("revenue_paid"),
        )
        .join(StudentSubscription, StudentSubscription.plan_id == Plan.id)
        .join(
            SubscriptionPayment,
            SubscriptionPayment.subscription_id == StudentSubscription.id,
        )
        .filter(
            Plan.gym_id == gym_id,
            SubscriptionPayment.status == "paid",
            SubscriptionPayment.paid_at.isnot(None),
            SubscriptionPayment.paid_at >= period_start,
            SubscriptionPayment.paid_at < period_end,
        )
        .group_by(Plan.id)
        .subquery()
    )

    q = (
        db.query(
            sub_counts.c.plan_id,
            sub_counts.c.plan_name,
            sub_counts.c.subscriptions_count,
            func.coalesce(revenue.c.revenue_paid, 0).label("revenue_paid"),
        )
        .outerjoin(revenue, revenue.c.plan_id == sub_counts.c.plan_id)
    )

    if sort_by == "revenue_paid":
        q = q.order_by(func.coalesce(revenue.c.revenue_paid, 0).desc())
    else:
        q = q.order_by(sub_counts.c.subscriptions_count.desc())

    rows = q.all()
    return [
        {
            "plan_id": r.plan_id,
            "plan_name": r.plan_name,
            "subscriptions_count": int(r.subscriptions_count or 0),
            "revenue_paid": Decimal(str(r.revenue_paid or 0)),
        }
        for r in rows
    ]
