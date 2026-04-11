from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.models.user import User
from app.models.student import Student
from app.models.gym import Gym
from app.core.security import hash_password
from app.core.roles import ADMIN_SISTEMA, ADMIN_ACADEMIA
from app.core.email_utils import normalize_email
from app.services.user_service import get_user_by_email
import os


def ensure_admin_exists(db: Session):
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("⚠️ ADMIN_EMAIL ou ADMIN_PASSWORD não definidos")
        return None

    admin_email = normalize_email(ADMIN_EMAIL)

    try:
        existing = get_user_by_email(db, admin_email)
    except OperationalError as e:
        err = str(e).lower()
        if "gym_id" in err or "academia_id" in err or "no such column" in err:
            print(
                "❌ Schema desatualizado: execute `alembic upgrade head` antes de subir a API."
            )
        else:
            print(f"❌ Erro ao consultar usuários: {e}")
        return None

    if existing:
        print("✅ Admin já existe")
        return existing

    scope = os.getenv("ADMIN_SCOPE", "academia").strip().lower()

    try:
        if scope == "sistema":
            user = User(
                gym_id=None,
                email=admin_email,
                password=hash_password(ADMIN_PASSWORD),
                role=ADMIN_SISTEMA,
                is_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(
                "🔥 Admin de sistema criado (use X-Gym-Id ou X-Academia-Id nas rotas por tenant)."
            )
            return user

        gym_id = int(
            os.getenv("ADMIN_GYM_ID", os.getenv("ADMIN_ACADEMIA_ID", "1"))
        )
        if db.query(Gym).filter(Gym.id == gym_id).first() is None:
            db.add(
                Gym(
                    id=gym_id,
                    name=(
                        os.getenv("ADMIN_GYM_NAME")
                        or os.getenv("ADMIN_ACADEMIA_NOME")
                        or "Main Gym"
                    ),
                    slug=f"gym-{gym_id}",
                )
            )
            db.commit()
            from app.services.tenant_saas_service import ensure_tenant_config

            ensure_tenant_config(db, gym_id)
            db.commit()

        user = User(
            gym_id=gym_id,
            email=admin_email,
            password=hash_password(ADMIN_PASSWORD),
            role=ADMIN_ACADEMIA,
            is_verified=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        student = Student(
            user_id=user.id,
            nome="Admin",
            telefone="",
            status="ativo",
        )

        db.add(student)
        db.commit()
        db.refresh(student)

        from app.services import student_modality_service as sm_svc

        sm_svc.ensure_default_enrollment(db, gym_id, student.id)
        db.commit()

        print("🔥 Admin do gym criado com sucesso!")

        return user

    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar admin: {e}")
        return None
