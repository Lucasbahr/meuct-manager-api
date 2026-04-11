from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_gym_id, require_staff
from app.db.deps import get_db
from app.models.student import Student
from app.schemas.response import ResponseBase
from app.schemas.training import TrainingCreate
from app.services import training_service as training_svc
from app.services import student_modality_service as sm_svc
from app.services.audit_service import ACTION_GRADUATION_REQUEST, record_audit_event

router = APIRouter(tags=["Training"])


class GraduationRequestBody(BaseModel):
    modality_id: int
    preferred_date: Optional[date] = None
    note: Optional[str] = Field(None, max_length=500)


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


@router.get("/training/me/graduation-eligibility", response_model=ResponseBase)
def my_graduation_eligibility(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    """Aluno: elegibilidade e próxima faixa por modalidade (para agendar graduação)."""
    st = db.query(Student).filter(Student.user_id == user["user_id"]).first()
    if not st:
        raise HTTPException(
            status_code=404, detail="Perfil de aluno não encontrado"
        )
    data = sm_svc.eligibility_snapshot(db, gym_id, st.id)
    return {
        "success": True,
        "message": "Elegibilidade para graduação por modalidade",
        "data": data,
    }


@router.post("/training/me/graduation-request", response_model=ResponseBase)
def post_graduation_request(
    body: GraduationRequestBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    """Aluno apto: registra pedido de agendamento (auditoria para a equipe)."""
    st = db.query(Student).filter(Student.user_id == user["user_id"]).first()
    if not st:
        raise HTTPException(
            status_code=404, detail="Perfil de aluno não encontrado"
        )
    rows = sm_svc.eligibility_snapshot(db, gym_id, st.id)
    row = next(
        (x for x in rows if x["modality_id"] == body.modality_id),
        None,
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Modalidade não encontrada na sua matrícula",
        )
    if not row.get("eligible_for_promotion"):
        raise HTTPException(
            status_code=400,
            detail="Você ainda não atingiu as horas necessárias para agendar esta graduação",
        )
    nxt = row.get("next_graduation")
    record_audit_event(
        db,
        actor_user_id=user["user_id"],
        gym_id=gym_id,
        action=ACTION_GRADUATION_REQUEST,
        target_type="student",
        target_id=st.id,
        details={
            "student_name": st.nome,
            "modality_id": body.modality_id,
            "preferred_date": (
                body.preferred_date.isoformat() if body.preferred_date else None
            ),
            "note": body.note,
            "next_graduation": nxt,
        },
    )
    db.commit()
    return {
        "success": True,
        "message": "Solicitação registrada. A equipe da academia irá confirmar.",
        "data": {"modality_id": body.modality_id},
    }
