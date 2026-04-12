from datetime import date

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_academy_admin, require_gym_id, require_system_admin
from app.core.roles import (
    ADMIN_SISTEMA,
    ADMIN_ACADEMIA,
    PROFESSOR,
    ALUNO,
    normalize_role,
    is_academy_admin,
)
from app.db.deps import get_db
from app.models.checkin import Checkin
from app.models.student import Student
from app.models.user import User
from app.schemas.response import ResponseBase
from app.schemas.sales_dashboard import PlatformAdminDashboardOut
from app.services import sales_dashboard_service as sales_dash
from app.services.user_service import create_user, get_user_by_email
from app.services.student_photo import delete_student_photo
from app.services.audit_service import (
    record_audit_event,
    ACTION_USER_ROLE_CHANGED,
    ACTION_USER_DELETED,
    ACTION_USER_PROVISIONED,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

_ROLE_INPUT = {
    "ADMIN_SISTEMA": ADMIN_SISTEMA,
    "ADMIN_ACADEMIA": ADMIN_ACADEMIA,
    "ADMIN": ADMIN_ACADEMIA,
    "PROFESSOR": PROFESSOR,
    "ALUNO": ALUNO,
}


class UserRoleUpdate(BaseModel):
    email: str
    role: str


class UserProvisionBody(BaseModel):
    """Cria usuário já verificado na academia do contexto (`X-Gym-Id` / gym do token)."""

    email: str
    password: str = Field(..., min_length=6)
    role: str


def _parse_target_role(raw: str) -> str:
    key = raw.strip().upper()
    if key not in _ROLE_INPUT:
        raise HTTPException(status_code=400, detail="Role inválida")
    return _ROLE_INPUT[key]


@router.post("/users/provision", response_model=ResponseBase)
def admin_provision_user(
    data: UserProvisionBody,
    db: Session = Depends(get_db),
    admin=Depends(require_academy_admin),
    gym_id: int = Depends(require_gym_id),
):
    """Admin academia ou admin sistema (com `X-Gym-Id`): cria login para equipe/aluno."""
    email = data.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email obrigatório")
    pwd = (data.password or "").strip()
    if len(pwd) < 6:
        raise HTTPException(
            status_code=400, detail="Senha deve ter pelo menos 6 caracteres",
        )

    new_role = _parse_target_role(data.role)
    if new_role == ADMIN_SISTEMA:
        raise HTTPException(
            status_code=400,
            detail="Perfil ADMIN_SISTEMA não pode ser criado por este endpoint",
        )

    actor_role = normalize_role(admin.get("role"))
    if actor_role == ADMIN_ACADEMIA and new_role not in {
        ADMIN_ACADEMIA,
        PROFESSOR,
        ALUNO,
    }:
        raise HTTPException(status_code=400, detail="Role inválida para admin da academia")

    if get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    user = create_user(
        db,
        email,
        pwd,
        role=new_role,
        gym_id=gym_id,
        is_verified=True,
    )
    record_audit_event(
        db,
        actor_user_id=admin["user_id"],
        gym_id=gym_id,
        action=ACTION_USER_PROVISIONED,
        target_type="user",
        target_id=user.id,
        details={"email": user.email, "role": new_role},
    )
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Usuário criado na academia (já pode fazer login)",
        "data": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "gym_id": user.gym_id,
        },
    }


@router.put("/users/role", response_model=ResponseBase)
def admin_set_user_role(
    data: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_academy_admin),
    gym_id: int = Depends(require_gym_id),
):
    email = data.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email obrigatório")

    new_role = _parse_target_role(data.role)
    actor_role = normalize_role(admin.get("role"))

    if actor_role == ADMIN_ACADEMIA and new_role == ADMIN_SISTEMA:
        raise HTTPException(
            status_code=403, detail="Apenas admin de sistema pode atribuir esse perfil"
        )

    if actor_role == ADMIN_ACADEMIA and new_role not in {
        ADMIN_ACADEMIA,
        PROFESSOR,
        ALUNO,
    }:
        raise HTTPException(status_code=400, detail="Role inválida para admin da academia")

    user = get_user_by_email(db, email)
    if not user or user.gym_id != gym_id:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin["user_id"] and not is_academy_admin(new_role):
        raise HTTPException(
            status_code=400, detail="Você não pode remover seu próprio acesso administrativo"
        )

    old_role = user.role
    user.role = new_role
    record_audit_event(
        db,
        actor_user_id=admin["user_id"],
        gym_id=gym_id,
        action=ACTION_USER_ROLE_CHANGED,
        target_type="user",
        target_id=user.id,
        details={"email": user.email, "old_role": old_role, "new_role": new_role},
    )
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
    _admin=Depends(require_academy_admin),
    gym_id: int = Depends(require_gym_id),
):
    user = (
        db.query(User)
        .filter(User.id == user_id, User.gym_id == gym_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    record_audit_event(
        db,
        actor_user_id=_admin["user_id"],
        gym_id=gym_id,
        action=ACTION_USER_DELETED,
        target_type="user",
        target_id=user.id,
        details={"deleted_email": user.email},
    )

    student = db.query(Student).filter(Student.user_id == user_id).first()
    if student:
        db.query(Checkin).filter(Checkin.student_id == student.id).delete(
            synchronize_session=False
        )
        delete_student_photo(student.foto_path)
        delete_student_photo(student.foto_atleta_path)
        db.delete(student)

    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": "User removido",
        "data": None,
    }


@router.get("/dashboard", response_model=ResponseBase)
def admin_platform_dashboard(
    _sys=Depends(require_system_admin),
    db: Session = Depends(get_db),
    days: int | None = Query(None, description="7 ou 30"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    top_academies_limit: int = Query(10, ge=1, le=50),
):
    if days is not None and days not in (7, 30):
        raise HTTPException(
            status_code=400, detail="days deve ser 7 ou 30, ou use date_from e date_to"
        )
    if (date_from is None) != (date_to is None):
        raise HTTPException(
            status_code=400, detail="Informe date_from e date_to juntos"
        )
    start, end = sales_dash.resolve_period(
        days=days, date_from=date_from, date_to=date_to
    )
    data = sales_dash.platform_admin_dashboard(
        db,
        period_start=start,
        period_end=end,
        top_limit=top_academies_limit,
    )
    return {
        "success": True,
        "message": "Dashboard da plataforma",
        "data": PlatformAdminDashboardOut.model_validate(data).model_dump(),
    }
