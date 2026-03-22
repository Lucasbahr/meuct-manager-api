from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.user import User
from app.core.security import hash_password, verify_password
from app.core.security import _create_token
from datetime import timedelta


# REGISTER
def register_user(db: Session, email: str, password: str):
    existing = db.query(User).filter(User.email == email).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    user = User(
        email=email, password=hash_password(password), role="ALUNO", is_verified=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # token de verificação
    token = create_email_verification_token(user.id)

    print(f"http://localhost:8000/auth/verify-email?token={token}")

    return user


# LOGIN (AGORA SÓ VALIDA)
def login_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()

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
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email já verificado")

    token = create_email_verification_token(user.id)

    print(f"http://localhost:8000/auth/verify-email?token={token}")

    return {"message": "Email de verificação reenviado"}


# RESET EMAIL
def send_reset_email(email: str, token: str):
    reset_url = f"http://localhost:8000/reset-password?token={token}"

    print(f"Reset de senha para: {email}")
    print(f"Link: {reset_url}")
