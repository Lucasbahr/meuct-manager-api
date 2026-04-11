"""Rotas SaaS multi-tenant (white-label). Tenant = Gym no banco."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import (
    get_optional_user,
    require_academy_admin,
    require_gym_id,
    require_system_admin,
)
from app.core.tenant import get_effective_gym_id
from app.db.deps import get_db
from app.models.gym import Gym
from app.schemas.response import ResponseBase
from app.schemas.tenant_saas import (
    GraduacaoCreate,
    ModalidadeCreate,
    TenantBrandingPatch,
    TenantCreate,
)
from app.services import tenant_saas_service as ts_svc
from app.services.gym_storage import provision_tenant_storage

router = APIRouter(tags=["SaaS Tenant"])


def _resolve_gym_for_read(
    db: Session,
    request: Request,
    user: Optional[dict],
    slug: Optional[str],
) -> Gym:
    if slug:
        g = ts_svc.get_gym_by_slug(db, slug)
        if not g:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")
        return g
    if user:
        gid = get_effective_gym_id(db, user, request)
        g = db.query(Gym).filter(Gym.id == gid).first()
        if not g:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")
        return g
    raise HTTPException(
        status_code=400,
        detail="Informe o parâmetro slug ou autentique-se com Bearer token",
    )


@router.post("/tenants", response_model=ResponseBase)
def create_tenant_route(
    body: TenantCreate,
    _system=Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    logo = str(body.logo_url) if body.logo_url else None
    g = ts_svc.create_tenant(
        db,
        nome=body.nome,
        slug=body.slug,
        logo_url=logo,
        cor_primaria=body.cor_primaria,
        cor_secundaria=body.cor_secundaria,
        cor_background=body.cor_background,
    )
    db.commit()
    db.refresh(g)
    provision_tenant_storage(g.id)
    return {
        "success": True,
        "message": "Academia (tenant) criada",
        "data": ts_svc.tenant_public_dict(g),
    }


@router.get("/tenants/{slug}", response_model=ResponseBase)
def get_tenant_by_slug_public(slug: str, db: Session = Depends(get_db)):
    g = ts_svc.get_gym_by_slug(db, slug)
    if not g or not g.is_active:
        raise HTTPException(status_code=404, detail="Academia não encontrada")
    return {
        "success": True,
        "message": "Dados públicos do tenant",
        "data": ts_svc.tenant_public_dict(g),
    }


@router.patch("/tenant/branding", response_model=ResponseBase)
def patch_tenant_branding(
    body: TenantBrandingPatch,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    """Admin academia: cores, logo e texto público consumidos pelo app."""
    patch = body.model_dump(exclude_unset=True)
    g = ts_svc.update_gym_branding(db, gym_id, patch)
    db.commit()
    db.refresh(g)
    return {
        "success": True,
        "message": "Aparência da academia atualizada",
        "data": ts_svc.tenant_public_dict(g),
    }


@router.get("/tenant/config", response_model=ResponseBase)
def get_tenant_full_config(
    request: Request,
    slug: Optional[str] = Query(
        None, description="Identificador da academia (white-label / deep link)"
    ),
    db: Session = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
):
    g = _resolve_gym_for_read(db, request, user, slug)
    if not g.is_active:
        raise HTTPException(status_code=404, detail="Tenant inativo")
    data = ts_svc.build_full_tenant_config(db, g)
    return {
        "success": True,
        "message": "Configuração completa do tenant",
        "data": data,
    }


@router.get("/modalidades", response_model=ResponseBase)
def list_modalidades_saas(
    request: Request,
    slug: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
):
    g = _resolve_gym_for_read(db, request, user, slug)
    if not g.is_active:
        raise HTTPException(status_code=404, detail="Tenant inativo")
    return {
        "success": True,
        "message": "Modalidades do tenant",
        "data": ts_svc.list_modalities_for_tenant(db, g.id),
    }


@router.post("/modalidades", response_model=ResponseBase)
def create_modalidade_saas(
    body: ModalidadeCreate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    m = ts_svc.create_modality_global(db, body.nome)
    db.commit()
    db.refresh(m)
    return {
        "success": True,
        "message": "Modalidade disponível no catálogo",
        "data": {"id": m.id, "nome": m.name},
    }


@router.get("/graduacoes", response_model=ResponseBase)
def list_graduacoes_saas(
    request: Request,
    modalidade_id: Optional[int] = Query(None, alias="modalidade_id"),
    slug: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
):
    g = _resolve_gym_for_read(db, request, user, slug)
    if not g.is_active:
        raise HTTPException(status_code=404, detail="Tenant inativo")
    return {
        "success": True,
        "message": "Graduações",
        "data": ts_svc.list_graduacoes(db, g.id, modalidade_id),
    }


@router.post("/graduacoes", response_model=ResponseBase)
def create_graduacao_saas(
    body: GraduacaoCreate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    g = ts_svc.create_graduacao_for_tenant(
        db,
        gym_id,
        modality_id=body.modalidade_id,
        nome=body.nome,
        ordem=body.ordem,
        required_hours=body.required_hours,
    )
    db.commit()
    db.refresh(g)
    return {
        "success": True,
        "message": "Graduação criada",
        "data": {
            "id": g.id,
            "modalidade_id": g.modality_id,
            "nome": g.name,
            "ordem": g.level,
            "required_hours": g.required_hours,
        },
    }


@router.get("/tenant/students", response_model=ResponseBase)
def list_students_saas_admin(
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    """Lista alunos do tenant (admin). Usa `/tenant/students` para não colidir com `POST /students/`."""
    return {
        "success": True,
        "message": "Alunos do tenant",
        "data": ts_svc.list_students_admin(db, gym_id),
    }
