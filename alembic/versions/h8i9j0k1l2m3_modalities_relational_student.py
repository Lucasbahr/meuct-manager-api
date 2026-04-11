"""modalidades/graduações relacionais; remove strings em students

Revision ID: h8i9j0k1l2m3
Revises: f7e8d9c0b1a2
Create Date: 2026-04-11

"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, Sequence[str], None] = "f7e8d9c0b1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MODALITY_CANONICAL = [
    "Muay Thai",
    "Jiu Jitsu",
    "Boxe",
    "K1",
]

DEFAULT_GRADUATION_LADDER: list[tuple[str, int, str]] = [
    ("Branca", 1, "0"),
    ("Amarela", 2, "40"),
    ("Verde", 3, "80"),
    ("Azul", 4, "120"),
    ("Roxa", 5, "180"),
    ("Marrom", 6, "240"),
    ("Preta", 7, "300"),
    ("Ponta preta", 8, "400"),
    ("Ponta vermelha", 9, "500"),
    ("Ponta amarela", 10, "600"),
]

MODALITY_ALIASES: dict[str, str] = {
    "muay thai": "Muay Thai",
    "muaythai": "Muay Thai",
    "muay-thai": "Muay Thai",
    "thai": "Muay Thai",
    "jiu jitsu": "Jiu Jitsu",
    "jiu-jitsu": "Jiu Jitsu",
    "jiujitsu": "Jiu Jitsu",
    "bjj": "Jiu Jitsu",
    "boxe": "Boxe",
    "boxing": "Boxe",
    "k1": "K1",
    "k-1": "K1",
    "kickboxing": "K1",
}

GRAD_ALIASES: dict[str, str] = {
    "branca": "Branca",
    "amarela": "Amarela",
    "amarelo": "Amarela",
    "verde": "Verde",
    "azul": "Azul",
    "roxa": "Roxa",
    "marrom": "Marrom",
    "preta": "Preta",
    "ponta preta": "Ponta preta",
    "ponta-preta": "Ponta preta",
    "ponta vermelha": "Ponta vermelha",
    "ponta amarela": "Ponta amarela",
}


def _norm_key(s: str | None) -> str:
    if not s:
        return ""
    t = s.lower().strip()
    t = re.sub(r"[\s_]+", " ", t)
    t = t.replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _has_table(insp: Any, name: str) -> bool:
    return insp.has_table(name)


def _has_column(insp: Any, table: str, column: str) -> bool:
    if not _has_table(insp, table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _create_modalities_table() -> None:
    op.create_table(
        "modalities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_modalities_name"),
    )
    op.create_index(op.f("ix_modalities_id"), "modalities", ["id"], unique=False)
    op.create_index(op.f("ix_modalities_name"), "modalities", ["name"], unique=True)


def _create_graduations_table() -> None:
    op.create_table(
        "graduations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gym_id", sa.Integer(), nullable=False),
        sa.Column("modality_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("required_hours", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["modality_id"], ["modalities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "gym_id", "modality_id", "level", name="uq_graduations_gym_modality_level"
        ),
    )
    op.create_index(op.f("ix_graduations_id"), "graduations", ["id"], unique=False)
    op.create_index(
        op.f("ix_graduations_gym_id"), "graduations", ["gym_id"], unique=False
    )
    op.create_index(
        op.f("ix_graduations_modality_id"), "graduations", ["modality_id"], unique=False
    )


def _create_student_modalities_table() -> None:
    op.create_table(
        "student_modalities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("modality_id", sa.Integer(), nullable=False),
        sa.Column("graduation_id", sa.Integer(), nullable=False),
        sa.Column("hours_trained", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["graduation_id"], ["graduations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["modality_id"], ["modalities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id", "modality_id", name="uq_student_modalities_student_modality"
        ),
    )
    op.create_index(
        op.f("ix_student_modalities_id"), "student_modalities", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_student_modalities_modality_id"),
        "student_modalities",
        ["modality_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_modalities_student_id"),
        "student_modalities",
        ["student_id"],
        unique=False,
    )


def _create_history_table() -> None:
    op.create_table(
        "student_graduation_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("modality_id", sa.Integer(), nullable=False),
        sa.Column("graduation_id", sa.Integer(), nullable=False),
        sa.Column("achieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hours_when_achieved", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["graduation_id"], ["graduations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["modality_id"], ["modalities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_student_graduation_history_id"),
        "student_graduation_history",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_graduation_history_modality_id"),
        "student_graduation_history",
        ["modality_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_graduation_history_student_id"),
        "student_graduation_history",
        ["student_id"],
        unique=False,
    )


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    dialect = bind.dialect.name

    if not _has_table(insp, "modalities"):
        _create_modalities_table()
        insp = sa.inspect(bind)
    if _has_table(insp, "modalities") and not _has_table(insp, "graduations"):
        _create_graduations_table()
        insp = sa.inspect(bind)
    if _has_table(insp, "graduations") and not _has_table(insp, "student_modalities"):
        _create_student_modalities_table()
        insp = sa.inspect(bind)
    if _has_table(insp, "student_modalities") and not _has_table(
        insp, "student_graduation_history"
    ):
        _create_history_table()
        insp = sa.inspect(bind)

    if _has_table(insp, "modalities"):
        ix_names = {i["name"] for i in insp.get_indexes("modalities")}
        if "ix_modalities_name" not in ix_names and "uq_modalities_name" not in ix_names:
            try:
                op.create_index(
                    "ix_modalities_name", "modalities", ["name"], unique=True
                )
            except Exception:
                pass

    for name in MODALITY_CANONICAL:
        if dialect == "sqlite":
            bind.execute(
                sa.text("INSERT OR IGNORE INTO modalities (name) VALUES (:n)").bindparams(
                    n=name
                )
            )
        else:
            bind.execute(
                sa.text(
                    "INSERT INTO modalities (name) VALUES (:n) "
                    "ON CONFLICT (name) DO NOTHING"
                ).bindparams(n=name)
            )

    mod_rows = bind.execute(sa.text("SELECT id, name FROM modalities")).mappings().all()
    modality_name_to_id = {r["name"]: r["id"] for r in mod_rows}

    gym_rows = bind.execute(sa.text("SELECT id FROM gyms")).mappings().all()
    gym_ids = [r["id"] for r in gym_rows] or [1]

    for gid in gym_ids:
        for _mname, mid in modality_name_to_id.items():
            for gname, level, req in DEFAULT_GRADUATION_LADDER:
                if dialect == "sqlite":
                    bind.execute(
                        sa.text(
                            "INSERT OR IGNORE INTO graduations "
                            "(gym_id, modality_id, name, level, required_hours) "
                            "VALUES (:g, :m, :n, :l, :r)"
                        ).bindparams(
                            g=gid, m=mid, n=gname, l=level, r=Decimal(req)
                        )
                    )
                else:
                    bind.execute(
                        sa.text(
                            "INSERT INTO graduations "
                            "(gym_id, modality_id, name, level, required_hours) "
                            "VALUES (:g, :m, :n, :l, :r) "
                            "ON CONFLICT (gym_id, modality_id, level) DO NOTHING"
                        ).bindparams(
                            g=gid, m=mid, n=gname, l=level, r=Decimal(req)
                        )
                    )

    had_legacy = _has_column(sa.inspect(bind), "students", "modalidade")
    if not had_legacy:
        return

    rows = bind.execute(
        sa.text(
            "SELECT s.id AS sid, u.gym_id AS gym_id, s.modalidade AS mod_s, "
            "s.graduacao AS grad_s, s.tempo_de_treino AS tempo "
            "FROM students s JOIN users u ON u.id = s.user_id"
        )
    ).mappings().all()

    for r in rows:
        sid = r["sid"]
        gym_id = r["gym_id"]
        if gym_id is None:
            continue
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM student_modalities WHERE student_id = :sid LIMIT 1"
            ).bindparams(sid=sid)
        ).scalar()
        if exists:
            continue

        mk = _norm_key(r["mod_s"])
        mcanon = MODALITY_ALIASES.get(mk)
        if not mcanon and mk:
            mcanon = MODALITY_ALIASES.get(mk.replace(" ", ""))
        if not mcanon:
            mcanon = "Muay Thai"
        mid = modality_name_to_id.get(mcanon) or modality_name_to_id.get("Muay Thai")

        gk = _norm_key(r["grad_s"])
        gcanon = GRAD_ALIASES.get(gk)
        if not gcanon and r["grad_s"]:
            gcanon = str(r["grad_s"]).strip()
        if not gcanon:
            gcanon = "Branca"

        grad_row = bind.execute(
            sa.text(
                "SELECT id FROM graduations WHERE gym_id = :g AND modality_id = :m "
                "AND lower(name) = lower(:n) LIMIT 1"
            ).bindparams(g=gym_id, m=mid, n=gcanon)
        ).mappings().first()

        if not grad_row:
            grad_row = bind.execute(
                sa.text(
                    "SELECT id FROM graduations WHERE gym_id = :g AND modality_id = :m "
                    "AND level = 1 LIMIT 1"
                ).bindparams(g=gym_id, m=mid)
            ).mappings().first()

        if not grad_row:
            continue

        gid_grad = grad_row["id"]
        hours = Decimal("0")
        if r["tempo"] is not None:
            try:
                hours = Decimal(str(r["tempo"]))
            except Exception:
                hours = Decimal("0")

        if dialect == "sqlite":
            bind.execute(
                sa.text(
                    "INSERT OR IGNORE INTO student_modalities "
                    "(student_id, modality_id, graduation_id, hours_trained) "
                    "VALUES (:s, :m, :g, :h)"
                ).bindparams(s=sid, m=mid, g=gid_grad, h=hours)
            )
        else:
            bind.execute(
                sa.text(
                    "INSERT INTO student_modalities "
                    "(student_id, modality_id, graduation_id, hours_trained) "
                    "VALUES (:s, :m, :g, :h) "
                    "ON CONFLICT (student_id, modality_id) DO NOTHING"
                ).bindparams(s=sid, m=mid, g=gid_grad, h=hours)
            )

    if dialect == "sqlite":
        with op.batch_alter_table("students") as batch_op:
            batch_op.drop_column("modalidade")
            batch_op.drop_column("graduacao")
    else:
        op.drop_column("students", "modalidade")
        op.drop_column("students", "graduacao")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("students") as batch_op:
            batch_op.add_column(sa.Column("modalidade", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("graduacao", sa.String(), nullable=True))
    else:
        op.add_column("students", sa.Column("modalidade", sa.String(), nullable=True))
        op.add_column("students", sa.Column("graduacao", sa.String(), nullable=True))
