"""add data_nascimento to students

Revision ID: fdc5b9156539
Revises: d9f7e2c3a5b4
Create Date: 2026-03-30 10:31:30.445384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdc5b9156539'
down_revision: Union[str, Sequence[str], None] = 'd9f7e2c3a5b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("students", sa.Column("data_nascimento", sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("students", "data_nascimento")
