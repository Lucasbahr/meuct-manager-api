"""Comissão interna da plataforma por pedido pago (cobrança posterior)."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class PlatformCommission(Base):
    __tablename__ = "commissions"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_commissions_order_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer,
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_amount = Column(Numeric(12, 2), nullable=False)
    commission_percentage = Column(Numeric(5, 2), nullable=False)
    commission_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(16), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)

    gym = relationship("Gym", back_populates="commissions")
    order = relationship("ShopOrder", back_populates="commission_row")
