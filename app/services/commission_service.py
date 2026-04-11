from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.core.commission_constants import (
    COMMISSION_STATUS_PENDING,
    PLATFORM_COMMISSION_PERCENT,
    PLATFORM_COMMISSION_RATE,
)
from app.models.commission import PlatformCommission
from app.models.marketplace import ShopOrder


def ensure_commission_for_paid_order(db: Session, order: ShopOrder) -> PlatformCommission | None:
    """
    Registra comissão de 3% sobre o total do pedido (idempotente por order_id).
    Chamado quando o pedido passa a status pago.
    """
    existing = (
        db.query(PlatformCommission)
        .filter(PlatformCommission.order_id == order.id)
        .first()
    )
    if existing:
        return None

    total = Decimal(str(order.total_amount))
    amt = (total * PLATFORM_COMMISSION_RATE).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    row = PlatformCommission(
        gym_id=order.gym_id,
        order_id=order.id,
        total_amount=order.total_amount,
        commission_percentage=PLATFORM_COMMISSION_PERCENT,
        commission_amount=amt,
        status=COMMISSION_STATUS_PENDING,
    )
    db.add(row)
    db.flush()
    return row
