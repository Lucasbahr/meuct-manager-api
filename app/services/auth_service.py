from sqlalchemy.orm import Session
import os
from fastapi import HTTPException
from app.models.user import User
from app.models.gym import Gym
from app.services.user_service import get_user_by_email
from app.core.security import hash_password, verify_password
from app.core.security import _create_token
from datetime import timedelta
from app.services.email_service import send_email
from app.core.email_utils import normalize_email

# REGISTER
def register_user(db: Session, email: str, password: str, gym_id: int = 1):
    email = normalize_email(email)
    if db.query(Gym).filter(Gym.id == gym_id).first() is None:
        raise HTTPException(status_code=400, detail="Gym inválido")
    existing = db.query(User).filter(User.email == email).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    user = User(
        gym_id=gym_id,
        email=email,
        password=hash_password(password),
        role="ALUNO",
        is_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # token de verificação
    token = create_email_verification_token(user.id)

    send_verification_email(user.email, token)

    return user


# LOGIN (AGORA SÓ VALIDA)
def login_user(db: Session, email: str, password: str):
    email = normalize_email(email)
    user = get_user_by_email(db, email)

    if not user or not verify_password(password, user.password):
        return None

    if not user.is_verified:
        raise HTTPException(status_code=400, detail="Email não verificado")

    return user


# EMAIL VERIFICATION TOKEN
def create_email_verification_token(user_id: int):
    return _create_token(
        {"user_id": user_id}, timedelta(hours=24), "email_verification"
    )


# RESEND EMAIL
def resend_verification_email(db: Session, email: str):
    email = normalize_email(email)
    user = get_user_by_email(db, email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email já verificado")

    token = create_email_verification_token(user.id)
    
    send_verification_email(user.email, token)

    return {"message": "Email de verificação reenviado com sucesso"}


# RESET EMAIL
def send_reset_email(email: str, token: str):
    link = f"{os.getenv('BASE_URL')}/auth/reset-password?token={token}"

    body = f"""
    <h2>Reset de senha</h2>
    <p>Clique abaixo:</p>

    <a href="{link}">Resetar senha</a>
    """

    send_email(
        to_email=email,
        subject="Reset de senha",
        body=body
    )


def send_verification_email(user_email: str, token: str):
    link = f"{os.getenv('BASE_URL')}/auth/verify-email?token={token}"

    body = f"""
    <h2>Confirme seu email</h2>
    <p>Clique no botão abaixo para ativar sua conta:</p>

    <a href="{link}" 
       style="display:inline-block;padding:12px 20px;background:#111;color:#fff;text-decoration:none;border-radius:5px;">
        Confirmar Email
    </a>

    <p>Se não funcionar, copie o link:</p>
    <p>{link}</p>
    """

    send_email(
        to_email=user_email,
        subject="Confirme seu email",
        body=body
    )