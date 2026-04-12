"""Regras de negócio SaaS: tenant = gym, isolamento por gym_id."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.gym import Gym
from app.models.graduation import Graduation
from app.models.marketplace import GymPaymentSettings
from app.models.modality import Modality
from app.models.student import Student
from app.models.tenant_config import TenantConfig
from app.models.user import User


def slugify_name(name: str) -> str:
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower().strip()
    n = re.sub(r"[^\w\s-]", "", n)
    n = re.sub(r"[-\s]+", "-", n).strip("-")
    return (n[:72] if n else "academia")


def allocate_unique_slug(db: Session, base: str) -> str:
    candidate = base
    n = 2
    while db.query(Gym).filter(Gym.slug == candidate).first():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def ensure_tenant_config(db: Session, gym_id: int) -> TenantConfig:
    row = db.query(TenantConfig).filter(TenantConfig.gym_id == gym_id).first()
    if row:
        return row
    row = TenantConfig(gym_id=gym_id)
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def normalize_payment_provider_label(provider: str) -> str:
    if provider == "mercado_pago":
        return "mercadopago"
    return provider


def get_gym_by_slug(db: Session, slug: str) -> Optional[Gym]:
    normalized = slugify_name(slug)
    return db.query(Gym).filter(Gym.slug == normalized).first()


def create_tenant(
    db: Session,
    *,
    nome: str,
    slug: Optional[str],
    logo_url: Optional[str],
    cor_primaria: Optional[str],
    cor_secundaria: Optional[str],
    cor_background: Optional[str],
) -> Gym:
    if slug:
        want = slugify_name(slug)
        if db.query(Gym).filter(Gym.slug == want).first():
            raise HTTPException(
                status_code=409, detail=f"Slug '{want}' já está em uso"
            )
        final_slug = want
    else:
        final_slug = allocate_unique_slug(db, slugify_name(nome))
    g = Gym(
        name=nome.strip(),
        slug=final_slug,
        logo_url=logo_url,
        cor_primaria=cor_primaria,
        cor_secundaria=cor_secundaria,
        cor_background=cor_background,
        is_active=True,
    )
    db.add(g)
    db.flush()
    ensure_tenant_config(db, g.id)
    db.refresh(g)
    return g


def tenant_public_dict(g: Gym) -> dict[str, Any]:
    return {
        "id": g.id,
        "nome": g.name,
        "slug": g.slug,
        "logo_url": g.logo_url,
        "cor_primaria": g.cor_primaria,
        "cor_secundaria": g.cor_secundaria,
        "cor_background": g.cor_background,
        "public_description": g.public_description,
        "ativo": g.is_active,
    }


_BRANDING_KEYS = frozenset(
    {
        "public_description",
        "cor_primaria",
        "cor_secundaria",
        "cor_background",
        "logo_url",
    }
)


def update_gym_branding(db: Session, gym_id: int, patch: Dict[str, Any]) -> Gym:
    g = db.query(Gym).filter(Gym.id == gym_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Academia não encontrada")
    for key, value in patch.items():
        if key not in _BRANDING_KEYS:
            continue
        setattr(g, key, value)
    return g


def tenant_config_dict(tc: TenantConfig) -> dict[str, Any]:
    return {
        "permite_checkin": tc.permite_checkin,
        "permite_agendamento": tc.permite_agendamento,
        "mostrar_ranking": tc.mostrar_ranking,
        "mostrar_graduacao": tc.mostrar_graduacao,
        "cobrar_mensalidade": tc.cobrar_mensalidade,
    }


def payment_configs_public(db: Session, gym_id: int) -> List[dict[str, Any]]:
    rows = (
        db.query(GymPaymentSettings)
        .filter(GymPaymentSettings.gym_id == gym_id)
        .all()
    )
    out: List[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "provider": normalize_payment_provider_label(row.provider),
                "public_key": row.public_key,
                "ativo": bool(row.access_token or row.client_id),
                "has_access_token_configured": bool(row.access_token),
            }
        )
    return out


def list_modalities_for_tenant(db: Session, gym_id: int) -> List[dict[str, Any]]:
    """Modalidades que possuem ao menos uma graduação neste tenant."""
    q = (
        db.query(Modality)
        .join(Graduation, Graduation.modality_id == Modality.id)
        .filter(Graduation.gym_id == gym_id)
        .distinct()
        .order_by(Modality.name.asc())
    )
    return [{"id": m.id, "nome": m.name} for m in q.all()]


def ensure_default_graduation_for_gym_modality(
    db: Session, gym_id: int, modality_id: int
) -> None:
    """
    Garante que a modalidade apareça em GET /modalidades para o tenant.

    A listagem só inclui modalidades com ao menos uma linha em `graduations`
    para aquele gym. O POST /modalidades só criava o registro global em
    `modalities`, deixando a lista vazia até existir uma graduação.
    """
    exists = (
        db.query(Graduation)
        .filter(
            Graduation.gym_id == gym_id,
            Graduation.modality_id == modality_id,
        )
        .first()
    )
    if exists:
        return
    g = Graduation(
        gym_id=gym_id,
        modality_id=modality_id,
        name="Iniciante",
        level=1,
        required_hours=Decimal("0"),
    )
    db.add(g)
    db.flush()


def list_graduacoes(
    db: Session, gym_id: int, modality_id: Optional[int]
) -> List[dict[str, Any]]:
    q = db.query(Graduation).filter(Graduation.gym_id == gym_id)
    if modality_id is not None:
        q = q.filter(Graduation.modality_id == modality_id)
    rows = q.order_by(Graduation.modality_id.asc(), Graduation.level.asc()).all()
    return [
        {
            "id": r.id,
            "modalidade_id": r.modality_id,
            "nome": r.name,
            "ordem": r.level,
            "required_hours": r.required_hours,
        }
        for r in rows
    ]


def create_modality_global(db: Session, nome: str) -> Modality:
    name = nome.strip()
    existing = db.query(Modality).filter(Modality.name == name).first()
    if existing:
        return existing
    m = Modality(name=name)
    db.add(m)
    db.flush()
    db.refresh(m)
    return m


def create_graduacao_for_tenant(
    db: Session,
    gym_id: int,
    *,
    modality_id: int,
    nome: str,
    ordem: int,
    required_hours: Decimal,
) -> Graduation:
    m = db.query(Modality).filter(Modality.id == modality_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Modalidade não encontrada")

    conflict = (
        db.query(Graduation)
        .filter(
            Graduation.gym_id == gym_id,
            Graduation.modality_id == modality_id,
            Graduation.level == ordem,
        )
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=400,
            detail="Já existe graduação com esta ordem nesta modalidade",
        )

    g = Graduation(
        gym_id=gym_id,
        modality_id=modality_id,
        name=nome.strip(),
        level=ordem,
        required_hours=required_hours,
    )
    db.add(g)
    db.flush()
    db.refresh(g)
    return g


def build_full_tenant_config(db: Session, gym: Gym) -> dict[str, Any]:
    tc = ensure_tenant_config(db, gym.id)
    return {
        "tenant": tenant_public_dict(gym),
        "config": tenant_config_dict(tc),
        "modalidades": list_modalities_for_tenant(db, gym.id),
        "graduacoes": list_graduacoes(db, gym.id, None),
        "payment_configs": payment_configs_public(db, gym.id),
    }


def list_students_admin(db: Session, gym_id: int) -> List[dict[str, Any]]:
    from app.services import student_modality_service as sm_svc

    query = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(User.gym_id == gym_id)
    )
    out = []
    for s in query.all():
        loaded = sm_svc.load_student_with_modalities(db, s.id) or s
        out.append(sm_svc.student_to_response(loaded).model_dump())
    return out
