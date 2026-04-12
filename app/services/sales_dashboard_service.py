from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, List, Optional, Tuple

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.commission import PlatformCommission
from app.models.gym import Gym
from app.models.marketplace import OrderItem, Product, ShopOrder
from app.services.marketplace_service import ORDER_PAID


def resolve_period(
    *,
    days: Optional[int],
    date_from: Optional[date],
    date_to: Optional[date],
) -> Tuple[datetime, datetime]:
    """Retorna [start inclusive, end exclusive) em UTC."""
    now = datetime.now(timezone.utc)
    if date_from is not None and date_to is not None:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        end = datetime.combine(date_to, time.min, tzinfo=timezone.utc) + timedelta(
            days=1
        )
        return start, end
    d = days if days in (7, 30) else 30
    end = now
    start = end - timedelta(days=d)
    return start, end


def _sales_day_expression(created_at_col, dialect_name: str):
    """Bucket diário compatível com SQLite e PostgreSQL."""
    if dialect_name == "sqlite":
        return func.strftime("%Y-%m-%d", created_at_col)
    return func.to_char(created_at_col, "YYYY-MM-DD")


def gym_sales_dashboard(
    db: Session,
    gym_id: int,
    *,
    period_start: datetime,
    period_end: datetime,
    top_limit: int = 10,
) -> dict[str, Any]:
    dialect_name = db.get_bind().dialect.name
    total_sales = (
        db.query(func.coalesce(func.sum(ShopOrder.total_amount), 0))
        .filter(
            ShopOrder.gym_id == gym_id,
            ShopOrder.status == ORDER_PAID,
            ShopOrder.created_at >= period_start,
            ShopOrder.created_at < period_end,
        )
        .scalar()
    )
    total_sales_dec = Decimal(str(total_sales or 0))

    total_orders = (
        db.query(func.count(ShopOrder.id))
        .filter(
            ShopOrder.gym_id == gym_id,
            ShopOrder.status == ORDER_PAID,
            ShopOrder.created_at >= period_start,
            ShopOrder.created_at < period_end,
        )
        .scalar()
        or 0
    )

    avg_ticket = (
        float(total_sales_dec / total_orders) if total_orders else 0.0
    )

    total_commission = (
        db.query(func.coalesce(func.sum(PlatformCommission.commission_amount), 0))
        .join(ShopOrder, ShopOrder.id == PlatformCommission.order_id)
        .filter(
            PlatformCommission.gym_id == gym_id,
            ShopOrder.status == ORDER_PAID,
            ShopOrder.created_at >= period_start,
            ShopOrder.created_at < period_end,
        )
        .scalar()
    )

    day_col = _sales_day_expression(ShopOrder.created_at, dialect_name)
    by_day_rows = (
        db.query(
            day_col.label("d"),
            func.coalesce(func.sum(ShopOrder.total_amount), 0).label("sales"),
            func.count(ShopOrder.id).label("orders"),
        )
        .filter(
            ShopOrder.gym_id == gym_id,
            ShopOrder.status == ORDER_PAID,
            ShopOrder.created_at >= period_start,
            ShopOrder.created_at < period_end,
        )
        .group_by(day_col)
        .order_by(day_col)
        .all()
    )
    sales_by_day: List[dict[str, Any]] = [
        {
            "date": str(r.d) if r.d is not None else None,
            "sales": float(r.sales or 0),
            "orders": int(r.orders or 0),
        }
        for r in by_day_rows
    ]

    line_revenue = OrderItem.price * OrderItem.quantity
    top_rows = (
        db.query(
            Product.id,
            Product.name,
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(line_revenue), 0).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(ShopOrder, ShopOrder.id == OrderItem.order_id)
        .filter(
            ShopOrder.gym_id == gym_id,
            ShopOrder.status == ORDER_PAID,
            ShopOrder.created_at >= period_start,
            ShopOrder.created_at < period_end,
        )
        .group_by(Product.id, Product.name)
        .order_by(desc(func.coalesce(func.sum(line_revenue), 0)))
        .limit(top_limit)
        .all()
    )
    top_products = [
        {
            "product_id": r.id,
            "name": r.name,
            "units_sold": int(r.units_sold or 0),
            "revenue": float(r.revenue or 0),
        }
        for r in top_rows
    ]

    return {
        "gym_id": gym_id,
        "period_start": period_start.isoformat(),
        "period_end_exclusive": period_end.isoformat(),
        "total_sales": float(total_sales_dec),
        "total_orders": int(total_orders),
        "average_ticket": round(avg_ticket, 2),
        "total_commission": float(Decimal(str(total_commission or 0))),
        "sales_by_day": sales_by_day,
        "top_products": top_products,
    }


def platform_admin_dashboard(
    db: Session,
    *,
    period_start: datetime,
    period_end: datetime,
    top_limit: int = 10,
) -> dict[str, Any]:
    total_revenue = (
        db.query(func.coalesce(func.sum(PlatformCommission.commission_amount), 0))
        .join(ShopOrder, ShopOrder.id == PlatformCommission.order_id)
        .filter(
            ShopOrder.status == ORDER_PAID,
            ShopOrder.created_at >= period_start,
            ShopOrder.created_at < period_end,
        )
        .scalar()
    )

    total_orders = (
        db.query(func.count(ShopOrder.id))
        .filter(
            ShopOrder.status == ORDER_PAID,
            ShopOrder.created_at >= period_start,
            ShopOrder.created_at < period_end,
        )
        .scalar()
        or 0
    )

    gyms_with_sales = (
        db.query(func.count(func.distinct(ShopOrder.gym_id)))
        .filter(
            ShopOrder.status == ORDER_PAID,
            ShopOrder.created_at >= period_start,
            ShopOrder.created_at < period_end,
        )
        .scalar()
        or 0
    )

    line_revenue = OrderItem.price * OrderItem.quantity
    top_rows = (
        db.query(
            Gym.id,
            Gym.name,
            func.coalesce(func.sum(ShopOrder.total_amount), 0).label("gross_sales"),
            func.coalesce(func.sum(PlatformCommission.commission_amount), 0).label(
                "commission"
            ),
            func.count(func.distinct(ShopOrder.id)).label("order_count"),
        )
        .select_from(Gym)
        .join(ShopOrder, ShopOrder.gym_id == Gym.id)
        .outerjoin(
            PlatformCommission, PlatformCommission.order_id == ShopOrder.id
        )
        .filter(
            ShopOrder.status == ORDER_PAID,
            ShopOrder.created_at >= period_start,
            ShopOrder.created_at < period_end,
        )
        .group_by(Gym.id, Gym.name)
        .order_by(desc(func.coalesce(func.sum(ShopOrder.total_amount), 0)))
        .limit(top_limit)
        .all()
    )

    top_academies = [
        {
            "gym_id": r.id,
            "name": r.name,
            "gross_sales": float(r.gross_sales or 0),
            "commission": float(Decimal(str(r.commission or 0))),
            "orders": int(r.order_count or 0),
        }
        for r in top_rows
    ]

    return {
        "period_start": period_start.isoformat(),
        "period_end_exclusive": period_end.isoformat(),
        "total_revenue": float(Decimal(str(total_revenue or 0))),
        "total_orders": int(total_orders),
        "total_academies": int(gyms_with_sales),
        "top_academies": top_academies,
    }
