from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.deps import get_db
from app.models.checkin import Checkin
from app.models.student import Student
from app.models.user import User
from app.schemas.response import ResponseBase
from app.services.student_photo import delete_student_photo

router = APIRouter(prefix="/admin", tags=["Admin"])


class UserRoleUpdate(BaseModel):
    email: str
    role: str


@router.put("/users/role", response_model=ResponseBase)
def admin_set_user_role(
    data: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    email = data.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email obrigatório")

    role = data.role.strip().upper()
    if role not in {"ADMIN", "ALUNO"}:
        raise HTTPException(status_code=400, detail="Role inválida")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Evita rebaixar o próprio admin em uso.
    if user.id == admin["user_id"] and role != "ADMIN":
        raise HTTPException(status_code=400, detail="Você não pode remover seu próprio admin")

    user.role = role
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Perfil de acesso atualizado",
        "data": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
        },
    }


@router.delete("/users/{user_id}", response_model=ResponseBase)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    student = db.query(Student).filter(Student.user_id == user_id).first()
    if student:
        db.query(Checkin).filter(Checkin.student_id == student.id).delete(
            synchronize_session=False
        )
        delete_student_photo(student.foto_path)
        db.delete(student)

    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": "User removido",
        "data": None,
    }

