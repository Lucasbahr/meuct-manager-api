from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password
from app.core.email_utils import normalize_email
from app.core.roles import ADMIN_SISTEMA, normalize_role


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Busca por email em minúsculas (login e .env podem divergir de maiúsculas no SQLite)."""
    normalized = normalize_email(email)
    if not normalized:
        return None
    return db.query(User).filter(func.lower(User.email) == normalized).first()


def create_user(
    db: Session,
    email: str,
    password: str,
    role: str = "ALUNO",
    is_verified: bool = True,
    gym_id: Optional[int] = 1,
):
    email = normalize_email(email)
    r = normalize_role(role)
    gid = None if r == ADMIN_SISTEMA else (gym_id if gym_id is not None else 1)
    user = User(
        gym_id=gid,
        email=email,
        password=hash_password(password),
        role=r,
        is_verified=is_verified,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
