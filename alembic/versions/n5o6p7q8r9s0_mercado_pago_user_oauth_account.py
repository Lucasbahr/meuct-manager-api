"""mercado_pago_accounts: OAuth Mercado Pago por usuário."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n5o6p7q8r9s0"
down_revision: Union[str, Sequence[str], None] = "m4n5o6p7q8r9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mercado_pago_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_in", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_mercado_pago_accounts_user_id"),
    )
    op.create_index(
        op.f("ix_mercado_pago_accounts_user_id"),
        "mercado_pago_accounts",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mercado_pago_accounts_id"),
        "mercado_pago_accounts",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_mercado_pago_accounts_id"), table_name="mercado_pago_accounts")
    op.drop_index(
        op.f("ix_mercado_pago_accounts_user_id"), table_name="mercado_pago_accounts"
    )
    op.drop_table("mercado_pago_accounts")
