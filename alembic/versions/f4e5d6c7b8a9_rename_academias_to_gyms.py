"""rename academias -> gyms, academia_id -> gym_id, nome -> name

Revision ID: f4e5d6c7b8a9
Revises: e2a3b4c5d6e7
Create Date: 2026-04-11

"""

from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4e5d6c7b8a9"
down_revision: Union[str, Sequence[str], None] = "e2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sqlite_rebuild_audit_events_without_academias_fk() -> None:
    """
    e2a3 cria FKs sem nome; no SQLite o reflexo devolve name=None e o batch não dropar.
    Recria a tabela mantendo só FK para users.
    """
    op.drop_index(op.f("ix_audit_events_created_at"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_action"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_academia_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_user_id"), table_name="audit_events")
    op.execute(
        sa.text(
            """
            CREATE TABLE audit_events__tmp (
                id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                academia_id INTEGER,
                action VARCHAR(64) NOT NULL,
                target_type VARCHAR(64),
                target_id INTEGER,
                details TEXT,
                created_at TIMESTAMP,
                PRIMARY KEY (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
    )
    op.execute(sa.text("INSERT INTO audit_events__tmp SELECT * FROM audit_events"))
    op.execute(sa.text("DROP TABLE audit_events"))
    op.execute(sa.text("ALTER TABLE audit_events__tmp RENAME TO audit_events"))
    op.create_index(
        op.f("ix_audit_events_user_id"), "audit_events", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_academia_id"),
        "audit_events",
        ["academia_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_action"), "audit_events", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_created_at"),
        "audit_events",
        ["created_at"],
        unique=False,
    )


def _drop_fks_to_referred(bind: Any, referred: str) -> None:
    """SQLite: batch para FKs nomeados; audit_events sem nome é recriada."""
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    if dialect == "sqlite":
        for table in insp.get_table_names():
            for fk in insp.get_foreign_keys(table):
                if fk.get("referred_table") != referred:
                    continue
                name = fk.get("name")
                if name:
                    with op.batch_alter_table(table) as batch_op:
                        batch_op.drop_constraint(name, type_="foreignkey")
        insp = sa.inspect(bind)
        if insp.has_table("audit_events"):
            for fk in insp.get_foreign_keys("audit_events"):
                if fk.get("referred_table") == referred and not fk.get("name"):
                    _sqlite_rebuild_audit_events_without_academias_fk()
                    break
        return

    for table in insp.get_table_names():
        for fk in insp.get_foreign_keys(table):
            if fk.get("referred_table") != referred:
                continue
            name = fk.get("name")
            if not name:
                continue
            op.drop_constraint(name, table, type_="foreignkey")


def _create_fk(
    bind: Any,
    table: str,
    constraint_name: str,
    ref_table: str,
    local_cols: list[str],
    remote_cols: list[str],
) -> None:
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table) as batch_op:
            batch_op.create_foreign_key(
                constraint_name, ref_table, local_cols, remote_cols
            )
    else:
        op.create_foreign_key(
            constraint_name, table, ref_table, local_cols, remote_cols
        )


def _drop_index_if(insp: Any, table: str, name: str) -> None:
    if not insp.has_table(table):
        return
    for ix in insp.get_indexes(table):
        if ix.get("name") == name:
            op.drop_index(name, table_name=table)
            return


def _has_column(insp: Any, table: str, col: str) -> bool:
    if not insp.has_table(table):
        return False
    return any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("academias"):
        return

    _drop_fks_to_referred(bind, "academias")

    _drop_index_if(insp, "users", "ix_users_academia_id")
    _drop_index_if(insp, "feed_items", "ix_feed_items_academia_id")
    _drop_index_if(insp, "audit_events", "ix_audit_events_academia_id")

    op.execute(sa.text("ALTER TABLE academias RENAME TO gyms"))

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER SEQUENCE IF EXISTS academias_id_seq RENAME TO gyms_id_seq"
            )
        )

    op.execute(sa.text("ALTER TABLE gyms RENAME COLUMN nome TO name"))

    if _has_column(insp, "users", "academia_id"):
        op.execute(sa.text("ALTER TABLE users RENAME COLUMN academia_id TO gym_id"))
    if _has_column(insp, "feed_items", "academia_id"):
        op.execute(
            sa.text("ALTER TABLE feed_items RENAME COLUMN academia_id TO gym_id")
        )
    if _has_column(insp, "audit_events", "academia_id"):
        op.execute(
            sa.text("ALTER TABLE audit_events RENAME COLUMN academia_id TO gym_id")
        )

    insp = sa.inspect(bind)
    if insp.has_table("graduations") and _has_column(insp, "graduations", "academy_id"):
        op.execute(
            sa.text("ALTER TABLE graduations RENAME COLUMN academy_id TO gym_id")
        )

    _create_fk(
        bind, "users", "fk_users_gym_id_gyms", "gyms", ["gym_id"], ["id"]
    )
    _create_fk(
        bind,
        "feed_items",
        "fk_feed_items_gym_id_gyms",
        "gyms",
        ["gym_id"],
        ["id"],
    )
    _create_fk(
        bind,
        "audit_events",
        "fk_audit_events_gym_id_gyms",
        "gyms",
        ["gym_id"],
        ["id"],
    )

    insp = sa.inspect(bind)
    if insp.has_table("graduations") and _has_column(insp, "graduations", "gym_id"):
        _create_fk(
            bind,
            "graduations",
            "fk_graduations_gym_id_gyms",
            "gyms",
            ["gym_id"],
            ["id"],
        )

    op.create_index("ix_users_gym_id", "users", ["gym_id"], unique=False)
    op.create_index("ix_feed_items_gym_id", "feed_items", ["gym_id"], unique=False)
    op.create_index(
        "ix_audit_events_gym_id", "audit_events", ["gym_id"], unique=False
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("gyms"):
        return

    _drop_fks_to_referred(bind, "gyms")

    _drop_index_if(insp, "users", "ix_users_gym_id")
    _drop_index_if(insp, "feed_items", "ix_feed_items_gym_id")
    _drop_index_if(insp, "audit_events", "ix_audit_events_gym_id")

    op.execute(sa.text("ALTER TABLE gyms RENAME TO academias"))
    op.execute(sa.text("ALTER TABLE academias RENAME COLUMN name TO nome"))

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER SEQUENCE IF EXISTS gyms_id_seq RENAME TO academias_id_seq"
            )
        )

    op.execute(sa.text("ALTER TABLE users RENAME COLUMN gym_id TO academia_id"))
    op.execute(sa.text("ALTER TABLE feed_items RENAME COLUMN gym_id TO academia_id"))
    op.execute(sa.text("ALTER TABLE audit_events RENAME COLUMN gym_id TO academia_id"))

    insp = sa.inspect(bind)
    if insp.has_table("graduations") and _has_column(insp, "graduations", "gym_id"):
        op.execute(
            sa.text("ALTER TABLE graduations RENAME COLUMN gym_id TO academy_id")
        )

    _create_fk(
        bind,
        "users",
        "fk_users_academia_id_academias",
        "academias",
        ["academia_id"],
        ["id"],
    )
    _create_fk(
        bind,
        "feed_items",
        "fk_feed_items_academia_id_academias",
        "academias",
        ["academia_id"],
        ["id"],
    )
    _create_fk(
        bind,
        "audit_events",
        "fk_audit_events_academia_id_academias",
        "academias",
        ["academia_id"],
        ["id"],
    )

    insp = sa.inspect(bind)
    if insp.has_table("graduations") and _has_column(
        insp, "graduations", "academy_id"
    ):
        _create_fk(
            bind,
            "graduations",
            "fk_graduations_academy_id_academias",
            "academias",
            ["academy_id"],
            ["id"],
        )

    op.create_index(
        "ix_users_academia_id", "users", ["academia_id"], unique=False
    )
    op.create_index(
        "ix_feed_items_academia_id",
        "feed_items",
        ["academia_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_academia_id",
        "audit_events",
        ["academia_id"],
        unique=False,
    )
