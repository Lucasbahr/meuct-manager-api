import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.models.student import Student
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.services.audit_service import record_audit_event, ACTION_LOGIN, ACTION_PASSWORD_CHANGED
from app.core.deps import get_current_user
from app.schemas.response import ResponseBase
from app.schemas.user import UserCreate, UserLogin
from app.services.auth_service import (
    register_user,
    login_user,
    send_reset_email,
    resend_verification_email,
)
from app.db.deps import get_db
from app.core.rate_limit import check_rate_limit, client_ip_from_request
from app.core.security import (
    decode_token,
    create_access_token,
    create_refresh_token,
    refresh_session_valid,
    revoke_refresh_token,
    create_reset_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.services.user_service import get_user_by_email
import logging
from app.core.email_utils import normalize_email

router = APIRouter(prefix="/auth", tags=["Auth"])


logger = logging.getLogger(__name__)


#  REGISTER
@router.post("/register", response_model=ResponseBase)
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    from app.services import tenant_saas_service as ts_svc

    allowed, retry_after = check_rate_limit(
        client_ip_from_request(request),
        bucket_key="auth_register",
        max_calls=10,
        window_seconds=3600,
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de registro. Tente mais tarde.",
            headers={"Retry-After": str(retry_after)},
        )

    reg_secret = (os.getenv("REGISTRATION_SECRET") or "").strip()
    if reg_secret:
        if not user.registration_secret or user.registration_secret != reg_secret:
            raise HTTPException(status_code=403, detail="Registro não autorizado")

    gid = user.gym_id
    if user.tenant_slug:
        g = ts_svc.get_gym_by_slug(db, user.tenant_slug)
        if not g or not g.is_active:
            raise HTTPException(
                status_code=400,
                detail="Academia (tenant) inválida ou inativa",
            )
        gid = g.id

    created_user = register_user(
        db, user.email, user.password, gym_id=gid
    )

    return {
        "success": True,
        "message": f"Usuário criado. Verifique seu email {created_user.email}",
        "data": {
            "id": created_user.id,
            "email": created_user.email,
            "role": created_user.role,
            "gym_id": created_user.gym_id,
        },
    }


#  LOGIN
@router.post("/login", response_model=ResponseBase)
def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    allowed, retry_after = check_rate_limit(
        client_ip_from_request(request),
        bucket_key="auth_login",
        max_calls=30,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Aguarde e tente novamente.",
            headers={"Retry-After": str(retry_after)},
        )

    db_user = login_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    db_user.last_login_at = datetime.now(timezone.utc)
    record_audit_event(
        db,
        actor_user_id=db_user.id,
        gym_id=db_user.gym_id,
        action=ACTION_LOGIN,
    )
    db.commit()

    token = create_access_token(
        {
            "sub": db_user.email,
            "user_id": db_user.id,
            "role": db_user.role,
            "gym_id": db_user.gym_id,
            "tenant_id": db_user.gym_id,
        }
    )
    refresh_token = create_refresh_token(
        {
            "sub": db_user.email,
            "user_id": db_user.id,
            "role": db_user.role,
            "gym_id": db_user.gym_id,
        }
    )

    return {
        "success": True,
        "message": "Login realizado com sucesso",
        "data": {"access_token": token, "refresh_token": refresh_token},
    }


@router.post("/refresh", response_model=ResponseBase)
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_token(refresh_token)
    if payload.get("error"):
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Tipo de token inválido")
    if not refresh_session_valid(refresh_token):
        raise HTTPException(status_code=401, detail="Sessão expirada")

    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    access_token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "role": user.role,
            "gym_id": user.gym_id,
            "tenant_id": user.gym_id,
        }
    )

    return {
        "success": True,
        "message": "Sessão renovada",
        "data": {"access_token": access_token},
    }


@router.post("/logout", response_model=ResponseBase)
def logout(refresh_token: str):
    revoke_refresh_token(refresh_token)
    return {"success": True, "message": "Logout realizado", "data": None}


#  VERIFY EMAIL
@router.get("/verify-email", response_model=ResponseBase)
def verify_email(token: str, db: Session = Depends(get_db)):
    payload = decode_token(token)

    if payload.get("error"):
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    if payload.get("type") != "email_verification":
        raise HTTPException(status_code=400, detail="Token inválido")

    user = db.query(User).filter(User.id == payload.get("user_id")).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    db.commit()

    student = Student(
        user_id=user.id,
        nome="",
        telefone="",
        status="ativo",
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    if user.gym_id is not None:
        from app.services import student_modality_service as sm_svc

        sm_svc.ensure_default_enrollment(db, user.gym_id, student.id)
        db.commit()

    return {"success": True, "message": "Email verificado com sucesso", "data": None}


#  RESEND EMAIL
@router.post("/resend-verification", response_model=ResponseBase)
def resend_verification(email: str = Query(...), db: Session = Depends(get_db)):
    resend_verification_email(db, normalize_email(email))

    return {
        "success": True,
        "message": "Se o email existir, um link foi enviado",
        "data": None,
    }


#  FORGOT PASSWORD
@router.post("/forgot-password", response_model=ResponseBase)
def forgot_password(email: str, db: Session = Depends(get_db)):
    email = normalize_email(email)
    user = get_user_by_email(db, email)

    if user:
        token = create_reset_token(user.email)
        send_reset_email(user.email, token)

    return {
        "success": True,
        "message": "Se o email existir, você receberá instruções",
        "data": None,
    }


#  RESET PASSWORD
@router.post("/reset-password", response_model=ResponseBase)
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    payload = decode_token(token)

    if payload.get("error"):
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    if payload.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Token inválido")

    email = payload.get("sub")

    if not email:
        raise HTTPException(status_code=400, detail="Token inválido")

    user = get_user_by_email(db, email)

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user.password = hash_password(new_password)
    user.password_reset_at = datetime.now(timezone.utc)
    record_audit_event(
        db,
        actor_user_id=user.id,
        gym_id=user.gym_id,
        action=ACTION_PASSWORD_CHANGED,
        details={"via": "reset_token"},
    )

    db.commit()

    return {"success": True, "message": "Senha redefinida com sucesso", "data": None}


#  CHANGE PASSWORD
@router.put("/change-password", response_model=ResponseBase)
def change_password(
    current_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()

    if not verify_password(current_password, user.password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    user.password = hash_password(new_password)
    record_audit_event(
        db,
        actor_user_id=user.id,
        gym_id=user.gym_id,
        action=ACTION_PASSWORD_CHANGED,
        details={"via": "authenticated_change"},
    )

    db.commit()

    return {"success": True, "message": "Senha alterada com sucesso", "data": None}
