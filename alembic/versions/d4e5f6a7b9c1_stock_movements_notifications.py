"""stock_movements, gym_notifications, products.track_stock

Revision ID: d4e5f6a7b9c1
Revises: c3d4e5f6a7b8
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "d4e5f6a7b9c1"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)

    product_cols = {c["name"] for c in insp.get_columns("products")}
    if "track_stock" not in product_cols:
        op.add_column(
            "products",
            sa.Column(
                "track_stock",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )

    if not insp.has_table("stock_movements"):
        op.create_table(
            "stock_movements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("gym_id", sa.Integer(), nullable=False),
            sa.Column("movement_type", sa.String(length=8), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("reason", sa.String(length=32), nullable=False),
            sa.Column("reference_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["reference_id"], ["orders.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_stock_movements_created_at"),
            "stock_movements",
            ["created_at"],
            unique=False,
        )
        op.create_index(
            op.f("ix_stock_movements_gym_id"),
            "stock_movements",
            ["gym_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_stock_movements_id"), "stock_movements", ["id"], unique=False
        )
        op.create_index(
            op.f("ix_stock_movements_movement_type"),
            "stock_movements",
            ["movement_type"],
            unique=False,
        )
        op.create_index(
            op.f("ix_stock_movements_product_id"),
            "stock_movements",
            ["product_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_stock_movements_reason"),
            "stock_movements",
            ["reason"],
            unique=False,
        )
        op.create_index(
            op.f("ix_stock_movements_reference_id"),
            "stock_movements",
            ["reference_id"],
            unique=False,
        )

    if not insp.has_table("gym_notifications"):
        op.create_table(
            "gym_notifications",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("gym_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("notification_type", sa.String(length=32), nullable=False),
            sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_gym_notifications_gym_id"),
            "gym_notifications",
            ["gym_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_gym_notifications_id"),
            "gym_notifications",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_gym_notifications_notification_type"),
            "gym_notifications",
            ["notification_type"],
            unique=False,
        )

    if insp.has_table("stock_movements"):
        n_movements = conn.execute(
            sa.text("SELECT COUNT(*) FROM stock_movements")
        ).scalar()
        if n_movements == 0:
            op.execute(
                sa.text(
                    """
                    INSERT INTO stock_movements
                        (product_id, gym_id, movement_type, quantity, reason, reference_id, created_at)
                    SELECT id, gym_id, 'IN', stock, 'adjustment', NULL, CURRENT_TIMESTAMP
                    FROM products
                    WHERE stock > 0
                    """
                )
            )

    # SQLite não implementa ALTER COLUMN ... DROP DEFAULT; Postgres sim.
    if conn.dialect.name != "sqlite":
        cols_after = {c["name"] for c in inspect(conn).get_columns("products")}
        if "track_stock" in cols_after:
            op.alter_column("products", "track_stock", server_default=None)


def downgrade() -> None:
    op.drop_index(
        op.f("ix_gym_notifications_notification_type"),
        table_name="gym_notifications",
    )
    op.drop_index(op.f("ix_gym_notifications_id"), table_name="gym_notifications")
    op.drop_index(op.f("ix_gym_notifications_gym_id"), table_name="gym_notifications")
    op.drop_table("gym_notifications")

    op.drop_index(
        op.f("ix_stock_movements_reference_id"), table_name="stock_movements"
    )
    op.drop_index(op.f("ix_stock_movements_reason"), table_name="stock_movements")
    op.drop_index(
        op.f("ix_stock_movements_product_id"), table_name="stock_movements"
    )
    op.drop_index(
        op.f("ix_stock_movements_movement_type"), table_name="stock_movements"
    )
    op.drop_index(op.f("ix_stock_movements_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_gym_id"), table_name="stock_movements")
    op.drop_index(
        op.f("ix_stock_movements_created_at"), table_name="stock_movements"
    )
    op.drop_table("stock_movements")

    op.drop_column("products", "track_stock")
