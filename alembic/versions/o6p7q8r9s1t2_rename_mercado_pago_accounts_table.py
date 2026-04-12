"""Renomeia mercado_pago_accounts -> mercadopago_accounts (OAuth por usuário)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o6p7q8r9s1t2"
down_revision: Union[str, Sequence[str], None] = "n5o6p7q8r9s0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    names = insp.get_table_names()
    if "mercadopago_accounts" in names:
        return
    if "mercado_pago_accounts" not in names:
        return
    op.rename_table("mercado_pago_accounts", "mercadopago_accounts")


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    names = insp.get_table_names()
    if "mercado_pago_accounts" in names:
        return
    if "mercadopago_accounts" not in names:
        return
    op.rename_table("mercadopago_accounts", "mercado_pago_accounts")
