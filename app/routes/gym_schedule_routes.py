"""Aulas da academia e grade horária semanal (consumo pelo app / site)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import (
    get_optional_user,
    require_academy_admin,
    require_gym_id,
)
from app.core.tenant import get_effective_gym_id
from app.db.deps import get_db
from app.models.gym import Gym
from app.schemas.gym_schedule import (
    GymClassCreate,
    GymClassUpdate,
    GymScheduleSlotCreate,
    GymScheduleSlotUpdate,
)
from app.schemas.response import ResponseBase
from app.services import gym_schedule_service as sch_svc
from app.services.tenant_saas_service import get_gym_by_slug

router = APIRouter(tags=["Grade horária"])


def _resolve_gym_for_public_read(
    db: Session,
    request: Request,
    user: Optional[dict],
    slug: Optional[str],
) -> Gym:
    if slug:
        g = get_gym_by_slug(db, slug)
        if not g:
            raise HTTPException(status_code=404, detail="Academia não encontrada")
        if not g.is_active:
            raise HTTPException(status_code=404, detail="Academia inativa")
        return g
    if user:
        gid = get_effective_gym_id(db, user, request)
        g = db.query(Gym).filter(Gym.id == gid).first()
        if not g:
            raise HTTPException(status_code=404, detail="Academia não encontrada")
        return g
    raise HTTPException(
        status_code=400,
        detail="Informe ?slug= da academia ou envie Authorization",
    )


# --- Leitura pública / autenticada (aluno ou visitante com slug) ---


@router.get("/gym-classes", response_model=ResponseBase)
def list_gym_classes_public(
    request: Request,
    slug: Optional[str] = Query(None, description="Slug da academia (white-label)"),
    active_only: bool = Query(
        True, description="Se true, só aulas ativas (recomendado para o app)"
    ),
    db: Session = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
):
    g = _resolve_gym_for_public_read(db, request, user, slug)
    data = sch_svc.list_gym_classes(db, g.id, active_only=active_only)
    return {"success": True, "message": "Aulas da academia", "data": data}


@router.get("/gym-schedule", response_model=ResponseBase)
def list_gym_schedule_public(
    request: Request,
    slug: Optional[str] = Query(None),
    active_only: bool = Query(True),
    grouped: bool = Query(
        False,
        description="Se true, agrupa horários por dia da semana",
    ),
    db: Session = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
):
    g = _resolve_gym_for_public_read(db, request, user, slug)
    if grouped:
        data = sch_svc.schedule_grouped_by_weekday(db, g.id, active_only=active_only)
        return {"success": True, "message": "Grade por dia", "data": data}
    data = sch_svc.list_schedule_slots(db, g.id, active_only=active_only)
    return {"success": True, "message": "Grade horária", "data": data}


# --- Admin academia: CRUD ---


@router.post("/gym-classes", response_model=ResponseBase)
def admin_create_gym_class(
    body: GymClassCreate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    row = sch_svc.create_gym_class(
        db,
        gym_id,
        name=body.name,
        description=body.description,
        modality_id=body.modality_id,
        instructor_name=body.instructor_name,
        duration_minutes=body.duration_minutes,
        sort_order=body.sort_order,
        is_active=body.is_active,
    )
    db.commit()
    db.refresh(row)
    return {
        "success": True,
        "message": "Aula cadastrada",
        "data": sch_svc.serialize_gym_class(row),
    }


@router.patch("/gym-classes/{class_id}", response_model=ResponseBase)
def admin_update_gym_class(
    class_id: int,
    body: GymClassUpdate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    patch = body.model_dump(exclude_unset=True)
    row = sch_svc.update_gym_class(db, gym_id, class_id, patch)
    db.commit()
    db.refresh(row)
    return {
        "success": True,
        "message": "Aula atualizada",
        "data": sch_svc.serialize_gym_class(row),
    }


@router.delete("/gym-classes/{class_id}", response_model=ResponseBase)
def admin_delete_gym_class(
    class_id: int,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    sch_svc.delete_gym_class(db, gym_id, class_id)
    db.commit()
    return {"success": True, "message": "Aula removida", "data": None}


@router.post("/gym-schedule/slots", response_model=ResponseBase)
def admin_create_schedule_slot(
    body: GymScheduleSlotCreate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    row = sch_svc.create_schedule_slot(
        db,
        gym_id,
        gym_class_id=body.gym_class_id,
        weekday=body.weekday,
        start_time=body.start_time,
        end_time=body.end_time,
        room=body.room,
        notes=body.notes,
        is_active=body.is_active,
    )
    db.commit()
    return {
        "success": True,
        "message": "Horário adicionado à grade",
        "data": sch_svc.serialize_schedule_slot(row),
    }


@router.patch("/gym-schedule/slots/{slot_id}", response_model=ResponseBase)
def admin_update_schedule_slot(
    slot_id: int,
    body: GymScheduleSlotUpdate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    patch = body.model_dump(exclude_unset=True)
    row = sch_svc.update_schedule_slot(db, gym_id, slot_id, patch)
    db.commit()
    return {
        "success": True,
        "message": "Horário atualizado",
        "data": sch_svc.serialize_schedule_slot(row),
    }


@router.delete("/gym-schedule/slots/{slot_id}", response_model=ResponseBase)
def admin_delete_schedule_slot(
    slot_id: int,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    sch_svc.delete_schedule_slot(db, gym_id, slot_id)
    db.commit()
    return {"success": True, "message": "Horário removido", "data": None}
