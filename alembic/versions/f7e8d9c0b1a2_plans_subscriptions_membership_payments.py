"""plans, student_subscriptions, subscription_payments

Revision ID: f7e8d9c0b1a2
Revises: e5f6a7b8c9d2
Create Date: 2026-04-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7e8d9c0b1a2"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plans_gym_id"), "plans", ["gym_id"], unique=False)
    op.create_index(op.f("ix_plans_id"), "plans", ["id"], unique=False)

    op.create_table(
        "student_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_student_subscriptions_id"), "student_subscriptions", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_student_subscriptions_plan_id"),
        "student_subscriptions",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_subscriptions_student_id"),
        "student_subscriptions",
        ["student_id"],
        unique=False,
    )

    op.create_table(
        "subscription_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["student_subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_subscription_payments_id"), "subscription_payments", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_subscription_payments_student_id"),
        "subscription_payments",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscription_payments_subscription_id"),
        "subscription_payments",
        ["subscription_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_subscription_payments_subscription_id"), table_name="subscription_payments"
    )
    op.drop_index(
        op.f("ix_subscription_payments_student_id"), table_name="subscription_payments"
    )
    op.drop_index(op.f("ix_subscription_payments_id"), table_name="subscription_payments")
    op.drop_table("subscription_payments")
    op.drop_index(
        op.f("ix_student_subscriptions_student_id"), table_name="student_subscriptions"
    )
    op.drop_index(
        op.f("ix_student_subscriptions_plan_id"), table_name="student_subscriptions"
    )
    op.drop_index(op.f("ix_student_subscriptions_id"), table_name="student_subscriptions")
    op.drop_table("student_subscriptions")
    op.drop_index(op.f("ix_plans_id"), table_name="plans")
    op.drop_index(op.f("ix_plans_gym_id"), table_name="plans")
    op.drop_table("plans")
