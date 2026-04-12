from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_academy_admin, require_gym_id
from app.db.deps import get_db
from app.schemas.membership import (
    PaymentResponse,
    PlanCreate,
    PlanResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionWithPaymentsResponse,
)
from app.schemas.response import ResponseBase
from app.services import membership_service as membership_svc

router = APIRouter(tags=["Membership"])


@router.post("/plans", response_model=ResponseBase)
def create_plan(
    data: PlanCreate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    plan = membership_svc.create_plan(
        db,
        gym_id,
        name=data.name,
        price=data.price,
        duration_days=data.duration_days,
        is_active=data.is_active,
    )
    return {
        "success": True,
        "message": "Plano criado",
        "data": PlanResponse.model_validate(plan),
    }


@router.get("/plans", response_model=ResponseBase)
def list_plans(
    active_only: bool = Query(False),
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    plans = membership_svc.list_plans(db, gym_id, active_only=active_only)
    return {
        "success": True,
        "message": "Planos",
        "data": [PlanResponse.model_validate(p) for p in plans],
    }


@router.post("/subscriptions", response_model=ResponseBase)
def create_subscription(
    data: SubscriptionCreate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    sub, pay = membership_svc.create_subscription(
        db,
        gym_id,
        student_id=data.student_id,
        plan_id=data.plan_id,
        start_date=data.start_date,
    )
    payload = SubscriptionWithPaymentsResponse(
        subscription=SubscriptionResponse.model_validate(sub),
        payments=[PaymentResponse.model_validate(pay)],
    )
    return {
        "success": True,
        "message": "Assinatura criada com primeiro pagamento",
        "data": payload.model_dump(),
    }


@router.post("/payments/{payment_id}/pay", response_model=ResponseBase)
def pay_subscription_payment(
    payment_id: int,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    pay = membership_svc.mark_payment_paid(db, gym_id, payment_id)
    return {
        "success": True,
        "message": "Pagamento registrado",
        "data": PaymentResponse.model_validate(pay),
    }
