"""Ledger de estoque: toda entrada/saída via movimentos; `products.stock` é cache."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.marketplace import Product, ShopOrder
from app.models.stock import GymNotification, StockMovement

MOV_IN = "IN"
MOV_OUT = "OUT"

REASON_PURCHASE = "purchase"
REASON_MANUAL = "manual"
REASON_LOSS = "loss"
REASON_CANCEL = "cancel"
REASON_ADJUSTMENT = "adjustment"
REASON_SALE = "sale"

NOTIF_SALE = "sale"
NOTIF_STOCK_LOW = "stock_low"
NOTIF_STOCK_OUT = "stock_out"

LOW_STOCK_THRESHOLD = 5


def _sum_movements(db: Session, product_id: int, movement_type: str) -> int:
    q = (
        db.query(func.coalesce(func.sum(StockMovement.quantity), 0))
        .filter(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == movement_type,
        )
        .scalar()
    )
    return int(q or 0)


def computed_quantity(db: Session, product_id: int) -> int:
    ins = _sum_movements(db, product_id, MOV_IN)
    outs = _sum_movements(db, product_id, MOV_OUT)
    return ins - outs


def get_stock(db: Session, product: Product) -> Optional[int]:
    if not product.track_stock:
        return None
    return computed_quantity(db, product.id)


def sync_stock_cache(db: Session, product: Product) -> None:
    if product.track_stock:
        product.stock = max(0, computed_quantity(db, product.id))
    db.flush()


def _assert_product_gym(product: Product, gym_id: int) -> None:
    if product.gym_id != gym_id:
        raise HTTPException(status_code=404, detail="Produto não encontrado")


def _notify(
    db: Session,
    gym_id: int,
    *,
    title: str,
    message: str,
    notification_type: str,
) -> None:
    db.add(
        GymNotification(
            gym_id=gym_id,
            title=title,
            message=message,
            notification_type=notification_type,
            is_read=False,
        )
    )


def _after_quantity_change(
    db: Session,
    gym_id: int,
    product: Product,
    old_qty: int,
    new_qty: int,
) -> None:
    if not product.track_stock:
        return
    if new_qty == 0 and old_qty > 0:
        _notify(
            db,
            gym_id,
            title="Produto esgotado",
            message=f'"{product.name}" ficou sem estoque.',
            notification_type=NOTIF_STOCK_OUT,
        )
    elif new_qty <= LOW_STOCK_THRESHOLD and old_qty > LOW_STOCK_THRESHOLD:
        _notify(
            db,
            gym_id,
            title="Estoque baixo",
            message=f'"{product.name}" está com {new_qty} unidade(s) (≤{LOW_STOCK_THRESHOLD}).',
            notification_type=NOTIF_STOCK_LOW,
        )


def record_movement(
    db: Session,
    gym_id: int,
    product_id: int,
    movement_type: str,
    quantity: int,
    reason: str,
    reference_id: Optional[int] = None,
) -> StockMovement:
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantidade deve ser positiva")
    if movement_type not in (MOV_IN, MOV_OUT):
        raise HTTPException(status_code=400, detail="Tipo de movimento inválido")

    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.gym_id == gym_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if not product.track_stock:
        raise HTTPException(
            status_code=400,
            detail="Este produto não controla estoque por movimentos",
        )

    old_qty = computed_quantity(db, product.id)

    if movement_type == MOV_OUT:
        if old_qty < quantity:
            raise HTTPException(status_code=400, detail="Estoque insuficiente")

    m = StockMovement(
        product_id=product_id,
        gym_id=gym_id,
        movement_type=movement_type,
        quantity=quantity,
        reason=reason,
        reference_id=reference_id,
    )
    db.add(m)
    db.flush()

    sync_stock_cache(db, product)
    new_qty = product.stock
    _after_quantity_change(db, gym_id, product, old_qty, new_qty)
    return m


def add_stock(
    db: Session, gym_id: int, product_id: int, quantity: int
) -> StockMovement:
    return record_movement(
        db, gym_id, product_id, MOV_IN, quantity, REASON_MANUAL
    )


def remove_stock(
    db: Session,
    gym_id: int,
    product_id: int,
    quantity: int,
    reason: str,
    reference_id: Optional[int] = None,
) -> StockMovement:
    allowed = {
        REASON_LOSS,
        REASON_MANUAL,
        REASON_ADJUSTMENT,
        REASON_CANCEL,
    }
    if reason not in allowed:
        raise HTTPException(status_code=400, detail="Motivo inválido para saída")
    return record_movement(
        db, gym_id, product_id, MOV_OUT, quantity, reason, reference_id
    )


def seed_initial_purchase(
    db: Session, gym_id: int, product_id: int, quantity: int
) -> None:
    """Criação do produto: entrada inicial (compra / estoque inicial)."""
    if quantity <= 0:
        return
    record_movement(
        db, gym_id, product_id, MOV_IN, quantity, REASON_PURCHASE
    )


def reconcile_stock_target(
    db: Session, gym_id: int, product_id: int, target: int
) -> None:
    """Ajusta estoque até o alvo usando movimentos de ajuste."""
    if target < 0:
        raise HTTPException(status_code=400, detail="Estoque não pode ser negativo")
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.gym_id == gym_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if not product.track_stock:
        raise HTTPException(status_code=400, detail="Produto sem controle de estoque")
    cur = computed_quantity(db, product_id)
    diff = target - cur
    if diff > 0:
        record_movement(
            db, gym_id, product_id, MOV_IN, diff, REASON_ADJUSTMENT
        )
    elif diff < 0:
        record_movement(
            db, gym_id, product_id, MOV_OUT, -diff, REASON_ADJUSTMENT
        )


def on_payment_approved(db: Session, order: ShopOrder) -> None:
    """Saída por venda + notificação de venda (chamado após marcar pedido pago)."""
    gym_id = order.gym_id
    for it in order.items:
        p = (
            db.query(Product)
            .filter(Product.id == it.product_id)
            .first()
        )
        if not p or not p.track_stock:
            continue
        record_movement(
            db,
            gym_id,
            it.product_id,
            MOV_OUT,
            it.quantity,
            REASON_SALE,
            reference_id=order.id,
        )

    total = float(order.total_amount)
    _notify(
        db,
        gym_id,
        title="Venda realizada",
        message=f"Pedido #{order.id} pago — total R$ {total:.2f}.",
        notification_type=NOTIF_SALE,
    )


def on_order_canceled(db: Session, order: ShopOrder) -> None:
    """
    Devolve estoque se o pedido já estava pago (cancelamento pós-pagamento).
    Pedidos pending/awaiting não consumiram movimento de venda.
    """
    if order.status != "paid":
        return
    gym_id = order.gym_id
    for it in order.items:
        p = (
            db.query(Product)
            .filter(Product.id == it.product_id)
            .first()
        )
        if not p or not p.track_stock:
            continue
        record_movement(
            db,
            gym_id,
            it.product_id,
            MOV_IN,
            it.quantity,
            REASON_CANCEL,
            reference_id=order.id,
        )


def list_movements(
    db: Session,
    gym_id: int,
    *,
    product_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    reason: Optional[str] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    sort_desc: bool = True,
    limit: Optional[int] = None,
) -> List[dict[str, Any]]:
    q = db.query(StockMovement).filter(StockMovement.gym_id == gym_id)
    if product_id is not None:
        q = q.filter(StockMovement.product_id == product_id)
    if movement_type is not None:
        q = q.filter(StockMovement.movement_type == movement_type)
    if reason is not None:
        q = q.filter(StockMovement.reason == reason)
    if created_from is not None:
        q = q.filter(StockMovement.created_at >= created_from)
    if created_to is not None:
        q = q.filter(StockMovement.created_at <= created_to)
    order_col = StockMovement.created_at.desc() if sort_desc else StockMovement.created_at.asc()
    q = q.order_by(order_col)
    if limit is not None:
        q = q.limit(limit)
    rows = q.all()
    return [
        {
            "id": m.id,
            "product_id": m.product_id,
            "gym_id": m.gym_id,
            "movement_type": m.movement_type,
            "quantity": m.quantity,
            "reason": m.reason,
            "reference_id": m.reference_id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]


def list_notifications(
    db: Session,
    gym_id: int,
    *,
    unread_only: bool = False,
    limit: int = 100,
) -> List[dict[str, Any]]:
    q = db.query(GymNotification).filter(GymNotification.gym_id == gym_id)
    if unread_only:
        q = q.filter(GymNotification.is_read.is_(False))
    rows = (
        q.order_by(GymNotification.created_at.desc()).limit(limit).all()
    )
    return [
        {
            "id": n.id,
            "gym_id": n.gym_id,
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


def mark_notification_read(
    db: Session, gym_id: int, notification_id: int
) -> None:
    n = (
        db.query(GymNotification)
        .filter(
            GymNotification.id == notification_id,
            GymNotification.gym_id == gym_id,
        )
        .first()
    )
    if not n:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    n.is_read = True
    db.flush()
