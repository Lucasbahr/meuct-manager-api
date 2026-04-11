from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_gym_id, require_staff
from app.db.deps import get_db
from app.schemas.response import ResponseBase
from app.schemas.student import StudentModalityCreateBody
from app.services import student_modality_service as sm_svc

router = APIRouter(tags=["Student modalities"])


@router.post("/student-modalities", response_model=ResponseBase)
def create_student_modality(
    body: StudentModalityCreateBody,
    _staff=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    hours = (
        body.hours_trained
        if body.hours_trained is not None
        else Decimal("0")
    )
    sm = sm_svc.add_student_modality(
        db,
        gym_id,
        student_id=body.student_id,
        modality_id=body.modality_id,
        graduation_id=body.graduation_id,
        hours_trained=hours,
    )
    db.commit()
    db.refresh(sm)
    items = sm_svc.list_student_modalities_items(db, gym_id, body.student_id)
    return {
        "success": True,
        "message": "Modalidade vinculada ao aluno",
        "data": [i.model_dump() for i in items],
    }
