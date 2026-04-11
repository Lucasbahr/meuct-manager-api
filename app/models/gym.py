from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class Gym(Base):
    """Tenant da aplicação (academia). `slug` identifica o white-label na URL/app."""

    __tablename__ = "gyms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(80), nullable=False, unique=True, index=True)
    logo_url = Column(String(1024), nullable=True)
    cor_primaria = Column(String(16), nullable=True)
    cor_secundaria = Column(String(16), nullable=True)
    cor_background = Column(String(16), nullable=True)
    public_description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=now_utc)

    tenant_config = relationship(
        "TenantConfig",
        back_populates="gym",
        uselist=False,
        cascade="all, delete-orphan",
    )

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
    gym_classes = relationship(
        "GymClass",
        back_populates="gym",
        cascade="all, delete-orphan",
    )
    gym_schedule_slots = relationship(
        "GymScheduleSlot",
        back_populates="gym",
        cascade="all, delete-orphan",
    )


# Alias semântico para documentação / imports explícitos SaaS
Tenant = Gym
