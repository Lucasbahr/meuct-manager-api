"""Loja por academia (tenant = gym). Pagamento direto na conta do provedor da academia."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class ProductCategory(Base):
    """Categoria de produtos por academia."""

    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint("gym_id", "name", name="uq_product_categories_gym_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(128), nullable=False)

    gym = relationship("Gym", back_populates="product_categories")
    subcategories = relationship(
        "ProductSubcategory",
        back_populates="category",
        cascade="all, delete-orphan",
    )
    products = relationship("Product", back_populates="category")


class ProductSubcategory(Base):
    __tablename__ = "product_subcategories"
    __table_args__ = (
        UniqueConstraint(
            "category_id", "name", name="uq_product_subcategories_category_name"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(
        Integer,
        ForeignKey("product_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(128), nullable=False)

    category = relationship("ProductCategory", back_populates="subcategories")
    products = relationship("Product", back_populates="subcategory")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id = Column(
        Integer,
        ForeignKey("product_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subcategory_id = Column(
        Integer,
        ForeignKey("product_subcategories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(12, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    track_stock = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)

    gym = relationship("Gym", back_populates="products")
    category = relationship("ProductCategory", back_populates="products")
    subcategory = relationship("ProductSubcategory", back_populates="products")
    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )
    order_items = relationship("OrderItem", back_populates="product")
    stock_movements = relationship(
        "StockMovement",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url = Column(String(1024), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    product = relationship("Product", back_populates="images")


class ShopOrder(Base):
    """Pedido na loja da academia (tabela `orders`)."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)
    payment_provider = Column(String(32), nullable=True)
    external_checkout_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)

    gym = relationship("Gym", back_populates="shop_orders")
    student = relationship("Student", back_populates="shop_orders")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    stock_movements = relationship(
        "StockMovement",
        back_populates="order",
    )
    commission_row = relationship(
        "PlatformCommission",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)

    order = relationship("ShopOrder", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class GymPaymentSettings(Base):
    """Credenciais do provedor; pagamento cai direto na conta configurada pela academia."""

    __tablename__ = "gym_payment_settings"
    __table_args__ = (
        UniqueConstraint("gym_id", "provider", name="uq_gym_payment_settings_gym_provider"),
    )

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider = Column(String(32), nullable=False)
    client_id = Column(String(512), nullable=True)
    client_secret = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    public_key = Column(String(512), nullable=True)

    gym = relationship("Gym", back_populates="payment_settings")


# Nome de domínio SaaS: credenciais por tenant; tokens em `access_token` (cifrados com Fernet quando configurado).
TenantPaymentConfig = GymPaymentSettings
