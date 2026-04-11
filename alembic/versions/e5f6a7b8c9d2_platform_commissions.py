"""platform commissions (3% por pedido pago)

Revision ID: e5f6a7b8c9d2
Revises: d4e5f6a7b9c1
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d2"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b9c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_commissions_order_id"),
    )
    op.create_index(op.f("ix_commissions_gym_id"), "commissions", ["gym_id"], unique=False)
    op.create_index(op.f("ix_commissions_id"), "commissions", ["id"], unique=False)
    op.create_index(
        op.f("ix_commissions_order_id"), "commissions", ["order_id"], unique=False
    )
    op.create_index(op.f("ix_commissions_status"), "commissions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_commissions_status"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_order_id"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_id"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_gym_id"), table_name="commissions")
    op.drop_table("commissions")
