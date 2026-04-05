"""student last fight and photo

Revision ID: c4f8a2b9e1d3
Revises: b2a4c8d1e5f6
Create Date: 2026-03-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4f8a2b9e1d3"
down_revision: Union[str, Sequence[str], None] = "b2a4c8d1e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("ultima_luta_em", sa.Date(), nullable=True),
    )
    op.add_column(
        "students",
        sa.Column("ultima_luta_modalidade", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "students",
        sa.Column("foto_path", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("students", "foto_path")
    op.drop_column("students", "ultima_luta_modalidade")
    op.drop_column("students", "ultima_luta_em")
