"""marketplace: products, categories, orders, payment settings

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f7
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "name", name="uq_product_categories_gym_name"),
    )
    op.create_index(
        op.f("ix_product_categories_gym_id"),
        "product_categories",
        ["gym_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_categories_id"), "product_categories", ["id"], unique=False
    )

    op.create_table(
        "product_subcategories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["product_categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "category_id", "name", name="uq_product_subcategories_category_name"
        ),
    )
    op.create_index(
        op.f("ix_product_subcategories_category_id"),
        "product_subcategories",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_subcategories_id"),
        "product_subcategories",
        ["id"],
        unique=False,
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("subcategory_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["product_categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subcategory_id"], ["product_subcategories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"], unique=False)
    op.create_index(op.f("ix_products_gym_id"), "products", ["gym_id"], unique=False)
    op.create_index(op.f("ix_products_id"), "products", ["id"], unique=False)
    op.create_index(
        op.f("ix_products_subcategory_id"), "products", ["subcategory_id"], unique=False
    )

    op.create_table(
        "gym_payment_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("client_id", sa.String(length=512), nullable=True),
        sa.Column("client_secret", sa.Text(), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "provider", name="uq_gym_payment_settings_gym_provider"),
    )
    op.create_index(
        op.f("ix_gym_payment_settings_gym_id"),
        "gym_payment_settings",
        ["gym_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gym_payment_settings_id"),
        "gym_payment_settings",
        ["id"],
        unique=False,
    )

    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_product_images_id"), "product_images", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_product_images_product_id"),
        "product_images",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payment_provider", sa.String(length=32), nullable=True),
        sa.Column("external_checkout_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_created_at"), "orders", ["created_at"], unique=False)
    op.create_index(op.f("ix_orders_external_checkout_id"), "orders", ["external_checkout_id"], unique=False)
    op.create_index(op.f("ix_orders_gym_id"), "orders", ["gym_id"], unique=False)
    op.create_index(op.f("ix_orders_id"), "orders", ["id"], unique=False)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)
    op.create_index(op.f("ix_orders_student_id"), "orders", ["student_id"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_id"), "order_items", ["id"], unique=False)
    op.create_index(
        op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False
    )
    op.create_index(
        op.f("ix_order_items_product_id"), "order_items", ["product_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_order_items_product_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_id"), table_name="order_items")
    op.drop_table("order_items")

    op.drop_index(op.f("ix_orders_student_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_gym_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_external_checkout_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_created_at"), table_name="orders")
    op.drop_table("orders")

    op.drop_index(op.f("ix_product_images_product_id"), table_name="product_images")
    op.drop_index(op.f("ix_product_images_id"), table_name="product_images")
    op.drop_table("product_images")

    op.drop_index(op.f("ix_gym_payment_settings_id"), table_name="gym_payment_settings")
    op.drop_index(op.f("ix_gym_payment_settings_gym_id"), table_name="gym_payment_settings")
    op.drop_table("gym_payment_settings")

    op.drop_index(op.f("ix_products_subcategory_id"), table_name="products")
    op.drop_index(op.f("ix_products_id"), table_name="products")
    op.drop_index(op.f("ix_products_gym_id"), table_name="products")
    op.drop_index(op.f("ix_products_category_id"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_product_subcategories_id"), table_name="product_subcategories")
    op.drop_index(
        op.f("ix_product_subcategories_category_id"), table_name="product_subcategories"
    )
    op.drop_table("product_subcategories")

    op.drop_index(op.f("ix_product_categories_id"), table_name="product_categories")
    op.drop_index(op.f("ix_product_categories_gym_id"), table_name="product_categories")
    op.drop_table("product_categories")
