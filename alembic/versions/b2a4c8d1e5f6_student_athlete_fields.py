"""student athlete fields

Revision ID: b2a4c8d1e5f6
Revises: 0b950391e732
Create Date: 2026-03-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2a4c8d1e5f6"
down_revision: Union[str, Sequence[str], None] = "0b950391e732"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column(
            "e_atleta",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("students", sa.Column("cartel_mma", sa.String(length=128), nullable=True))
    op.add_column("students", sa.Column("cartel_jiu", sa.String(length=128), nullable=True))
    op.add_column("students", sa.Column("cartel_k1", sa.String(length=128), nullable=True))
    op.add_column("students", sa.Column("nivel_competicao", sa.String(length=32), nullable=True))
    op.add_column("students", sa.Column("link_tapology", sa.String(length=512), nullable=True))
    # Keep server_default to remain compatible with SQLite migrations.


def downgrade() -> None:
    op.drop_column("students", "link_tapology")
    op.drop_column("students", "nivel_competicao")
    op.drop_column("students", "cartel_k1")
    op.drop_column("students", "cartel_jiu")
    op.drop_column("students", "cartel_mma")
    op.drop_column("students", "e_atleta")
