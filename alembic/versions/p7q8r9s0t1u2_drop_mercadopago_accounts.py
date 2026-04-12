"""Remove mercadopago_accounts (só credencial da academia em gym_payment_settings)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p7q8r9s0t1u2"
down_revision: Union[str, Sequence[str], None] = "o6p7q8r9s1t2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "mercadopago_accounts" not in insp.get_table_names():
        return
    op.drop_table("mercadopago_accounts")


def downgrade() -> None:
    op.create_table(
        "mercadopago_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_in", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_mercadopago_accounts_user_id"),
    )
    op.create_index(
        op.f("ix_mercadopago_accounts_user_id"),
        "mercadopago_accounts",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mercadopago_accounts_id"),
        "mercadopago_accounts",
        ["id"],
        unique=False,
    )
