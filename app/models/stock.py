"""Movimentação de estoque e notificações por academia (gym_id)."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gym_id = Column(
        Integer,
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    movement_type = Column(String(8), nullable=False, index=True)  # IN | OUT
    quantity = Column(Integer, nullable=False)
    reason = Column(String(32), nullable=False, index=True)
    reference_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)

    product = relationship("Product", back_populates="stock_movements")
    gym = relationship("Gym", back_populates="stock_movements")
    order = relationship("ShopOrder", back_populates="stock_movements")


class GymNotification(Base):
    __tablename__ = "gym_notifications"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer,
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(32), nullable=False, index=True)
    # Coluna SQL "read" — atributo Python is_read (evita sombra de builtin).
    is_read = Column("read", Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)

    gym = relationship("Gym", back_populates="notifications")
