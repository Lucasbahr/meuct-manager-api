"""Student e_professor + modalidades em que leciona.

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-04-05

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m4n5o6p7q8r9"
down_revision: Union[str, Sequence[str], None] = "l3m4n5o6p7q8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column(
            "e_professor",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "student_professor_modalities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("modality_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["modality_id"], ["modalities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "modality_id",
            name="uq_student_professor_mod_student_modality",
        ),
    )
    op.create_index(
        op.f("ix_student_professor_modalities_id"),
        "student_professor_modalities",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_professor_modalities_modality_id"),
        "student_professor_modalities",
        ["modality_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_professor_modalities_student_id"),
        "student_professor_modalities",
        ["student_id"],
        unique=False,
    )
    op.alter_column("students", "e_professor", server_default=None)


def downgrade() -> None:
    op.drop_index(
        op.f("ix_student_professor_modalities_student_id"),
        table_name="student_professor_modalities",
    )
    op.drop_index(
        op.f("ix_student_professor_modalities_modality_id"),
        table_name="student_professor_modalities",
    )
    op.drop_index(
        op.f("ix_student_professor_modalities_id"),
        table_name="student_professor_modalities",
    )
    op.drop_table("student_professor_modalities")
    op.drop_column("students", "e_professor")
