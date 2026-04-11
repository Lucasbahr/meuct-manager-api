from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_gym_id, require_staff
from app.db.deps import get_db
from app.schemas.response import ResponseBase
from app.schemas.training import TrainingCreate
from app.services import training_service as training_svc

router = APIRouter(tags=["Training"])


@router.post("/training", response_model=ResponseBase)
def register_training(
    body: TrainingCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    training_svc.can_access_student_training(db, user, body.student_id, gym_id)
    data = training_svc.add_training(
        db, body.student_id, body.modality_id, body.hours, gym_id
    )
    db.commit()
    return {
        "success": True,
        "message": "Treino registrado",
        "data": data,
    }


@router.get("/students/{student_id}/progress", response_model=ResponseBase)
def get_student_progress(
    student_id: int,
    modality_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    training_svc.can_access_student_training(db, user, student_id, gym_id)
    data = training_svc.student_progress(db, student_id, modality_id, gym_id)
    return {
        "success": True,
        "message": "Progresso por modalidade",
        "data": data,
    }


@router.post("/students/{student_id}/graduate", response_model=ResponseBase)
def graduate_student_route(
    student_id: int,
    modality_id: int = Query(..., description="Modalidade em que promover"),
    _staff=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    data = training_svc.graduate_student(db, student_id, modality_id, gym_id)
    db.commit()
    return {
        "success": True,
        "message": "Graduação atualizada",
        "data": data,
    }


@router.get("/students/{student_id}/gamification", response_model=ResponseBase)
def get_student_gamification(
    student_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    training_svc.can_access_student_training(db, user, student_id, gym_id)
    data = training_svc.gamification_snapshot(db, student_id, gym_id)
    db.commit()
    return {
        "success": True,
        "message": "Gamificação",
        "data": data,
    }


@router.get("/ranking", response_model=ResponseBase)
def get_ranking(
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
    limit: int = Query(10, ge=1, le=100),
):
    data = training_svc.ranking_top(db, gym_id, limit=limit)
    return {
        "success": True,
        "message": "Ranking por XP",
        "data": data,
    }
