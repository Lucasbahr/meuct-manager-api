from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(128), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    duration_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    gym = relationship("Gym", back_populates="plans")
    subscriptions = relationship("StudentSubscription", back_populates="plan")


class StudentSubscription(Base):
    __tablename__ = "student_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id = Column(
        Integer, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), default=now_utc)

    student = relationship("Student", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    payments = relationship(
        "SubscriptionPayment",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )


class SubscriptionPayment(Base):
    """Pagamentos de mensalidade (tabela `subscription_payments`)."""

    __tablename__ = "subscription_payments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id = Column(
        Integer,
        ForeignKey("student_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    due_date = Column(Date, nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    student = relationship("Student", back_populates="subscription_payments")
    subscription = relationship("StudentSubscription", back_populates="payments")
