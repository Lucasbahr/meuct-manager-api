"""SaaS: branding do tenant (gym), tenant_configs, public_key em pagamentos

Revision ID: i0j1k2l3m4n5
Revises: h8i9j0k1l2m3
Create Date: 2026-04-05

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i0j1k2l3m4n5"
down_revision: Union[str, Sequence[str], None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("gyms") as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("logo_url", sa.String(1024), nullable=True))
        batch_op.add_column(sa.Column("cor_primaria", sa.String(16), nullable=True))
        batch_op.add_column(sa.Column("cor_secundaria", sa.String(16), nullable=True))
        batch_op.add_column(sa.Column("cor_background", sa.String(16), nullable=True))
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )

    bind.execute(
        sa.text("UPDATE gyms SET slug = 'gym-' || CAST(id AS TEXT) WHERE slug IS NULL")
    )

    with op.batch_alter_table("gyms") as batch_op:
        batch_op.alter_column("slug", nullable=False)
        batch_op.create_unique_constraint("uq_gyms_slug", ["slug"])

    op.create_table(
        "tenant_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("permite_checkin", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "permite_agendamento", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("mostrar_ranking", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "mostrar_graduacao", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column(
            "cobrar_mensalidade", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("gym_id", name="uq_tenant_configs_gym_id"),
    )
    op.create_index("ix_tenant_configs_gym_id", "tenant_configs", ["gym_id"])

    rows = bind.execute(sa.text("SELECT id FROM gyms")).fetchall()
    for (gid,) in rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO tenant_configs (
                    gym_id, permite_checkin, permite_agendamento,
                    mostrar_ranking, mostrar_graduacao, cobrar_mensalidade
                ) VALUES (
                    :gid, 1, 0, 1, 1, 0
                )
                """
            ),
            {"gid": gid},
        )

    with op.batch_alter_table("gym_payment_settings") as batch_op:
        batch_op.add_column(sa.Column("public_key", sa.String(512), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("gym_payment_settings") as batch_op:
        batch_op.drop_column("public_key")

    op.drop_index("ix_tenant_configs_gym_id", table_name="tenant_configs")
    op.drop_table("tenant_configs")

    with op.batch_alter_table("gyms") as batch_op:
        batch_op.drop_constraint("uq_gyms_slug", type_="unique")
        batch_op.drop_column("is_active")
        batch_op.drop_column("cor_background")
        batch_op.drop_column("cor_secundaria")
        batch_op.drop_column("cor_primaria")
        batch_op.drop_column("logo_url")
        batch_op.drop_column("slug")
