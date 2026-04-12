"""gym_classes e gym_schedule_slots (aulas + grade horária)

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-04-05

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, Sequence[str], None] = "i0j1k2l3m4n5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gym_classes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("modality_id", sa.Integer(), nullable=True),
        sa.Column("instructor_name", sa.String(255), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["modality_id"], ["modalities.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("gym_id", "name", name="uq_gym_classes_gym_name"),
    )
    op.create_index("ix_gym_classes_gym_id", "gym_classes", ["gym_id"])
    op.create_index("ix_gym_classes_modality_id", "gym_classes", ["modality_id"])

    op.create_table(
        "gym_schedule_slots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("gym_class_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("room", sa.String(128), nullable=True),
        sa.Column("notes", sa.String(512), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.CheckConstraint(
            "weekday >= 0 AND weekday <= 6", name="ck_gym_schedule_weekday"
        ),
        sa.CheckConstraint("end_time > start_time", name="ck_gym_schedule_time_order"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["gym_class_id"], ["gym_classes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_gym_schedule_slots_gym_id", "gym_schedule_slots", ["gym_id"])
    op.create_index(
        "ix_gym_schedule_slots_gym_class_id", "gym_schedule_slots", ["gym_class_id"]
    )
    op.create_index(
        "ix_gym_schedule_slots_weekday", "gym_schedule_slots", ["weekday"]
    )


def downgrade() -> None:
    op.drop_index("ix_gym_schedule_slots_weekday", table_name="gym_schedule_slots")
    op.drop_index("ix_gym_schedule_slots_gym_class_id", table_name="gym_schedule_slots")
    op.drop_index("ix_gym_schedule_slots_gym_id", table_name="gym_schedule_slots")
    op.drop_table("gym_schedule_slots")
    op.drop_index("ix_gym_classes_modality_id", table_name="gym_classes")
    op.drop_index("ix_gym_classes_gym_id", table_name="gym_classes")
    op.drop_table("gym_classes")
