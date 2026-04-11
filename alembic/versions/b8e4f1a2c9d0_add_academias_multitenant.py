"""add academias multitenant (users + feed_items)

Revision ID: b8e4f1a2c9d0
Revises: f3a1b2c3d4e5
Create Date: 2026-04-05

"""

from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8e4f1a2c9d0"
down_revision: Union[str, Sequence[str], None] = "f3a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

IX_USERS_ACADEMIA = "ix_users_academia_id"
IX_FEED_ACADEMIA = "ix_feed_items_academia_id"


def _has_table(insp: Any, name: str) -> bool:
    return insp.has_table(name)


def _has_column(insp: Any, table: str, column: str) -> bool:
    if not _has_table(insp, table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_index(insp: Any, table: str, index_name: str) -> bool:
    if not _has_table(insp, table):
        return False
    return any(ix.get("name") == index_name for ix in insp.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not _has_table(insp, "academias"):
        op.create_table(
            "academias",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("nome", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute(
        sa.text(
            "INSERT INTO academias (id, nome) SELECT 1, 'Academia Principal' "
            "WHERE NOT EXISTS (SELECT 1 FROM academias WHERE id = 1)"
        )
    )

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "SELECT setval(pg_get_serial_sequence('academias', 'id'), "
                "(SELECT COALESCE(MAX(id), 1) FROM academias))"
            )
        )

    if not _has_column(insp, "users", "academia_id"):
        op.add_column(
            "users",
            sa.Column("academia_id", sa.Integer(), nullable=True),
        )
        op.execute(sa.text("UPDATE users SET academia_id = 1 WHERE academia_id IS NULL"))
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("users") as batch_op:
                batch_op.alter_column(
                    "academia_id",
                    existing_type=sa.Integer(),
                    nullable=False,
                    existing_nullable=True,
                )
                batch_op.create_foreign_key(
                    "fk_users_academia_id_academias",
                    "academias",
                    ["academia_id"],
                    ["id"],
                )
        else:
            op.alter_column(
                "users", "academia_id", existing_type=sa.Integer(), nullable=False
            )
            op.create_foreign_key(
                "fk_users_academia_id_academias",
                "users",
                "academias",
                ["academia_id"],
                ["id"],
            )

    insp = sa.inspect(bind)
    if not _has_index(insp, "users", IX_USERS_ACADEMIA):
        op.create_index(
            op.f("ix_users_academia_id"), "users", ["academia_id"], unique=False
        )

    insp = sa.inspect(bind)
    if not _has_column(insp, "feed_items", "academia_id"):
        op.add_column(
            "feed_items",
            sa.Column("academia_id", sa.Integer(), nullable=True),
        )
        op.execute(
            sa.text(
                "UPDATE feed_items SET academia_id = "
                "(SELECT u.academia_id FROM users u WHERE u.id = feed_items.created_by) "
                "WHERE academia_id IS NULL"
            )
        )
        op.execute(
            sa.text("UPDATE feed_items SET academia_id = 1 WHERE academia_id IS NULL")
        )
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("feed_items") as batch_op:
                batch_op.alter_column(
                    "academia_id",
                    existing_type=sa.Integer(),
                    nullable=False,
                    existing_nullable=True,
                )
                batch_op.create_foreign_key(
                    "fk_feed_items_academia_id_academias",
                    "academias",
                    ["academia_id"],
                    ["id"],
                )
        else:
            op.alter_column(
                "feed_items", "academia_id", existing_type=sa.Integer(), nullable=False
            )
            op.create_foreign_key(
                "fk_feed_items_academia_id_academias",
                "feed_items",
                "academias",
                ["academia_id"],
                ["id"],
            )

    insp = sa.inspect(bind)
    if not _has_index(insp, "feed_items", IX_FEED_ACADEMIA):
        op.create_index(
            op.f("ix_feed_items_academia_id"),
            "feed_items",
            ["academia_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_constraint("fk_feed_items_academia_id_academias", "feed_items", type_="foreignkey")
    op.drop_index(op.f("ix_feed_items_academia_id"), table_name="feed_items")
    op.drop_column("feed_items", "academia_id")

    op.drop_constraint("fk_users_academia_id_academias", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_academia_id"), table_name="users")
    op.drop_column("users", "academia_id")

    op.drop_table("academias")
