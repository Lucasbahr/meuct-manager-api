from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    price: Decimal = Field(..., ge=0, description="0 = plano gratuito")
    duration_days: int = Field(..., gt=0, le=3660)
    is_active: bool = True


class PlanResponse(BaseModel):
    id: int
    gym_id: int
    name: str
    price: Decimal
    duration_days: int
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SubscriptionCreate(BaseModel):
    student_id: int
    plan_id: int
    start_date: Optional[date] = None


class SubscriptionResponse(BaseModel):
    id: int
    student_id: int
    plan_id: int
    start_date: date
    end_date: date
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaymentResponse(BaseModel):
    id: int
    student_id: int
    subscription_id: int
    amount: Decimal
    status: str
    due_date: date
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SubscriptionWithPaymentsResponse(BaseModel):
    subscription: SubscriptionResponse
    payments: List[PaymentResponse]


class StudentAlertItem(BaseModel):
    student_id: int
    student_name: Optional[str] = None
    subscription_id: int
    plan_id: int
    plan_name: str
    payment_id: Optional[int] = None
    amount: Optional[Decimal] = None
    due_date: Optional[date] = None
    subscription_status: str
    reason: str


class StudentsAlertsOut(BaseModel):
    due_soon: List[StudentAlertItem]
    overdue: List[StudentAlertItem]


class FinancialReportOut(BaseModel):
    total_received: Decimal
    total_pending: Decimal
    total_overdue: Decimal
    total_payments: int


class StudentsReportOut(BaseModel):
    total_students: int
    active_students: int
    overdue_students: int
    canceled_students: int


class RevenueDayRow(BaseModel):
    day: str
    amount: Decimal
    count: int


class PlanSalesRow(BaseModel):
    plan_id: int
    plan_name: str
    subscriptions_count: int
    revenue_paid: Decimal
