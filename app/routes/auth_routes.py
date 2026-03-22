from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.student import Student
from sqlalchemy.orm import Session
from datetime import datetime, timezone
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
from app.core.security import (
    decode_token,
    create_access_token,
    create_reset_token,
    hash_password,
    verify_password,
)
from app.models.user import User
import logging

router = APIRouter(prefix="/auth", tags=["Auth"])


logger = logging.getLogger(__name__)


#  REGISTER
@router.post("/register", response_model=ResponseBase)
def register(user: UserCreate, db: Session = Depends(get_db)):
    created_user = register_user(db, user.email, user.password)

    return {
        "success": True,
        "message": f"Usuário criado. Verifique seu email {created_user.email}",
        "data": {
            "id": created_user.id,
            "email": created_user.email,
            "role": created_user.role,
        },
    }


#  LOGIN
@router.post("/login", response_model=ResponseBase)
def login(user: UserLogin, db: Session = Depends(get_db)):

    db_user = login_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_access_token(
        {"sub": db_user.email, "user_id": db_user.id, "role": db_user.role}
    )

    return {
        "success": True,
        "message": "Login realizado com sucesso",
        "data": {"access_token": token},
    }


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
        modalidade="Muay-Thai",
        graduacao="Branca",
        status="ativo",
    )

    db.add(student)
    db.commit()

    return {"success": True, "message": "Email verificado com sucesso", "data": None}


#  RESEND EMAIL
@router.post("/resend-verification", response_model=ResponseBase)
def resend_verification(email: str = Query(...), db: Session = Depends(get_db)):
    resend_verification_email(db, email)

    return {
        "success": True,
        "message": "Se o email existir, um link foi enviado",
        "data": None,
    }


#  FORGOT PASSWORD
@router.post("/forgot-password", response_model=ResponseBase)
def forgot_password(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()

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

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user.password = hash_password(new_password)
    user.password_reset_at = datetime.now(timezone.utc)

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

    db.commit()

    return {"success": True, "message": "Senha alterada com sucesso", "data": None}
