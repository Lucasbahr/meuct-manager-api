"""feed items, likes and comments

Revision ID: d9f7e2c3a5b4
Revises: c4f8a2b9e1d3
Create Date: 2026-03-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d9f7e2c3a5b4"
down_revision: Union[str, Sequence[str], None] = "c4f8a2b9e1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    op.create_index(op.f("ix_feed_likes_feed_item_id"), "feed_likes", ["feed_item_id"], unique=False)
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
    op.create_index(op.f("ix_feed_comments_feed_item_id"), "feed_comments", ["feed_item_id"], unique=False)
    op.create_index(op.f("ix_feed_comments_user_id"), "feed_comments", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_feed_comments_user_id"), table_name="feed_comments")
    op.drop_index(op.f("ix_feed_comments_feed_item_id"), table_name="feed_comments")
    op.drop_table("feed_comments")

    op.drop_index(op.f("ix_feed_likes_user_id"), table_name="feed_likes")
    op.drop_index(op.f("ix_feed_likes_feed_item_id"), table_name="feed_likes")
    op.drop_table("feed_likes")

    op.drop_index(op.f("ix_feed_items_created_by"), table_name="feed_items")
    op.drop_table("feed_items")

