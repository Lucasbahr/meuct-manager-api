"""student foto_atleta_path for athlete card

Revision ID: e1a2b3c4d5e6
Revises: d9f7e2c3a5b4
Create Date: 2026-03-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d9f7e2c3a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("foto_atleta_path", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("students", "foto_atleta_path")
