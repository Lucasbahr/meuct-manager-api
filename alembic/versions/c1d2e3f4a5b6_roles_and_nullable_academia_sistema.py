"""roles ADMIN_SISTEMA etc + users.academia_id nullable for sistema

Revision ID: c1d2e3f4a5b6
Revises: b8e4f1a2c9d0
Create Date: 2026-04-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b8e4f1a2c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE users SET role = 'ADMIN_ACADEMIA' WHERE role = 'ADMIN'")
    )
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "academia_id",
                existing_type=sa.Integer(),
                nullable=True,
                existing_nullable=False,
            )
    else:
        op.alter_column(
            "users",
            "academia_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE users SET academia_id = 1 WHERE academia_id IS NULL AND role != 'ADMIN_SISTEMA'"
        )
    )
    op.execute(sa.text("UPDATE users SET role = 'ADMIN' WHERE role = 'ADMIN_ACADEMIA'"))
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "academia_id",
                existing_type=sa.Integer(),
                nullable=False,
                existing_nullable=True,
            )
    else:
        op.alter_column(
            "users",
            "academia_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
