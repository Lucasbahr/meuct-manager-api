from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class Gym(Base):
    __tablename__ = "gyms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    users = relationship("User", back_populates="gym")
    graduations = relationship(
        "Graduation", back_populates="gym", cascade="all, delete-orphan"
    )
    product_categories = relationship(
        "ProductCategory",
        back_populates="gym",
        cascade="all, delete-orphan",
    )
    products = relationship(
        "Product",
        back_populates="gym",
        cascade="all, delete-orphan",
    )
    shop_orders = relationship(
        "ShopOrder",
        back_populates="gym",
        cascade="all, delete-orphan",
    )
    payment_settings = relationship(
        "GymPaymentSettings",
        back_populates="gym",
        cascade="all, delete-orphan",
    )
    stock_movements = relationship(
        "StockMovement",
        back_populates="gym",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "GymNotification",
        back_populates="gym",
        cascade="all, delete-orphan",
    )
    commissions = relationship(
        "PlatformCommission",
        back_populates="gym",
        cascade="all, delete-orphan",
    )
    plans = relationship(
        "Plan",
        back_populates="gym",
        cascade="all, delete-orphan",
    )
