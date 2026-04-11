"""student_stats, xp_logs, badges, student_badges

Revision ID: a1b2c3d4e5f7
Revises: f4e5d6c7b8a9
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "f4e5d6c7b8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("total_xp", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("current_streak", sa.Integer(), nullable=False),
        sa.Column("best_streak", sa.Integer(), nullable=False),
        sa.Column("last_training_date", sa.Date(), nullable=True),
        sa.Column("training_sessions_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id"),
    )
    op.create_index(
        op.f("ix_student_stats_id"), "student_stats", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_student_stats_student_id"),
        "student_stats",
        ["student_id"],
        unique=True,
    )

    op.create_table(
        "badges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_badges_id"), "badges", ["id"], unique=False)
    op.create_index(op.f("ix_badges_name"), "badges", ["name"], unique=True)

    op.create_table(
        "xp_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_xp_logs_id"), "xp_logs", ["id"], unique=False)
    op.create_index(
        op.f("ix_xp_logs_student_id"), "xp_logs", ["student_id"], unique=False
    )
    op.create_index(
        op.f("ix_xp_logs_source"), "xp_logs", ["source"], unique=False
    )

    op.create_table(
        "student_badges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("badge_id", sa.Integer(), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id", "badge_id", name="uq_student_badges_student_badge"
        ),
    )
    op.create_index(
        op.f("ix_student_badges_id"), "student_badges", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_student_badges_student_id"),
        "student_badges",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_badges_badge_id"),
        "student_badges",
        ["badge_id"],
        unique=False,
    )

    bind = op.get_bind()
    badge_rows = [
        ("FIRST_GRADUATION", "Primeira graduação", "belt"),
        ("STREAK_7", "7 dias de consistência", "flame"),
        ("WARRIOR_100", "100 treinos", "trophy"),
    ]
    for name, desc, icon in badge_rows:
        if bind.dialect.name == "sqlite":
            op.execute(
                sa.text(
                    "INSERT OR IGNORE INTO badges (name, description, icon) "
                    "VALUES (:n, :d, :i)"
                ).bindparams(n=name, d=desc, i=icon)
            )
        else:
            op.execute(
                sa.text(
                    "INSERT INTO badges (name, description, icon) "
                    "VALUES (:n, :d, :i) ON CONFLICT (name) DO NOTHING"
                ).bindparams(n=name, d=desc, i=icon)
            )


def downgrade() -> None:
    op.drop_index(op.f("ix_student_badges_badge_id"), table_name="student_badges")
    op.drop_index(op.f("ix_student_badges_student_id"), table_name="student_badges")
    op.drop_index(op.f("ix_student_badges_id"), table_name="student_badges")
    op.drop_table("student_badges")

    op.drop_index(op.f("ix_xp_logs_source"), table_name="xp_logs")
    op.drop_index(op.f("ix_xp_logs_student_id"), table_name="xp_logs")
    op.drop_index(op.f("ix_xp_logs_id"), table_name="xp_logs")
    op.drop_table("xp_logs")

    op.drop_index(op.f("ix_badges_name"), table_name="badges")
    op.drop_index(op.f("ix_badges_id"), table_name="badges")
    op.drop_table("badges")

    op.drop_index(op.f("ix_student_stats_student_id"), table_name="student_stats")
    op.drop_index(op.f("ix_student_stats_id"), table_name="student_stats")
    op.drop_table("student_stats")
