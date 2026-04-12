"""feed_items.imagem_link — URL ao tocar na foto

Revision ID: f3a1b2c3d4e5
Revises: 7c2d9e4f8a1b
Create Date: 2026-04-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "7c2d9e4f8a1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_feed_tables() -> None:
    """If feed_items is missing, create feed schema (same as d9f7e2c3a5b4).

    Handles databases where alembic_version was stamped ahead of d9f7.
    """
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "feed_items" in insp.get_table_names():
        return

    op.create_table(
        "feed_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("titulo", sa.String(length=128), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("evento_data", sa.Date(), nullable=True),
        sa.Column("local", sa.String(length=128), nullable=True),
        sa.Column("modalidade", sa.String(length=64), nullable=True),
        sa.Column("graduacao", sa.String(length=64), nullable=True),
        sa.Column("image_path", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feed_items_created_by"), "feed_items", ["created_by"], unique=False
    )

    op.create_table(
        "feed_likes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feed_item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["feed_item_id"], ["feed_items.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_item_id", "user_id", name="uq_feed_like_item_user"),
    )
    op.create_index(
        op.f("ix_feed_likes_feed_item_id"), "feed_likes", ["feed_item_id"], unique=False
    )
    op.create_index(op.f("ix_feed_likes_user_id"), "feed_likes", ["user_id"], unique=False)

    op.create_table(
        "feed_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feed_item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["feed_item_id"], ["feed_items.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feed_comments_feed_item_id"),
        "feed_comments",
        ["feed_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_feed_comments_user_id"), "feed_comments", ["user_id"], unique=False
    )


def upgrade() -> None:
    _ensure_feed_tables()
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("feed_items")}
    if "imagem_link" not in cols:
        op.add_column(
            "feed_items",
            sa.Column("imagem_link", sa.String(length=1024), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "feed_items" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("feed_items")}
    if "imagem_link" in cols:
        op.drop_column("feed_items", "imagem_link")
