"""Check-in vinculado à grade (slot) + horas creditadas.

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-04-11

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l3m4n5o6p7q8"
down_revision: Union[str, Sequence[str], None] = "k2l3m4n5o6p7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("checkins") as batch_op:
        batch_op.add_column(
            sa.Column("gym_schedule_slot_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("hours_credited", sa.Numeric(10, 2), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_checkins_gym_schedule_slot",
            "gym_schedule_slots",
            ["gym_schedule_slot_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_checkins_gym_schedule_slot_id",
            ["gym_schedule_slot_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("checkins") as batch_op:
        batch_op.drop_index("ix_checkins_gym_schedule_slot_id")
        batch_op.drop_constraint("fk_checkins_gym_schedule_slot", type_="foreignkey")
        batch_op.drop_column("hours_credited")
        batch_op.drop_column("gym_schedule_slot_id")
