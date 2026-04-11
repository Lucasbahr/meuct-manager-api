"""Texto público da academia (descrição / sobre) para o app.

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-04-11

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, Sequence[str], None] = "j1k2l3m4n5o6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("gyms") as batch_op:
        batch_op.add_column(
            sa.Column("public_description", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("gyms") as batch_op:
        batch_op.drop_column("public_description")
