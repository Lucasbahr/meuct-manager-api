from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password
from app.core.email_utils import normalize_email


def create_user(
    db: Session,
    email: str,
    password: str,
    role: str = "ALUNO",
    is_verified: bool = True,
):
    email = normalize_email(email)
    user = User(
        email=email,
        password=hash_password(password),
        role=role,
        is_verified=is_verified,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
