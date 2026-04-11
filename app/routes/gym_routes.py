from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.gym import Gym
from app.schemas.gym import GymCreate, GymResponse
from app.schemas.response import ResponseBase
from app.services.gym_storage import provision_tenant_storage
from app.services.tenant_saas_service import (
    allocate_unique_slug,
    ensure_tenant_config,
    slugify_name,
)

router = APIRouter(prefix="/gyms", tags=["Gyms"])


@router.get("", response_model=ResponseBase)
def list_gyms(db: Session = Depends(get_db)):
    rows = db.query(Gym).order_by(Gym.id.asc()).all()
    return {
        "success": True,
        "message": "Gyms",
        "data": [GymResponse.model_validate(g) for g in rows],
    }


@router.post("", response_model=ResponseBase)
def create_gym(data: GymCreate, db: Session = Depends(get_db)):
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Gym name is required")
    slug = allocate_unique_slug(db, slugify_name(name))
    g = Gym(name=name, slug=slug)
    db.add(g)
    db.flush()
    ensure_tenant_config(db, g.id)
    db.commit()
    db.refresh(g)
    provision_tenant_storage(g.id)
    return {
        "success": True,
        "message": "Gym created",
        "data": GymResponse.model_validate(g),
    }
