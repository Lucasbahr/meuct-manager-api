from sqlalchemy.orm import Session
from app.models.user import User
from app.models.student import Student
from app.core.security import hash_password
import os


def ensure_admin_exists(db: Session):
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("⚠️ ADMIN_EMAIL ou ADMIN_PASSWORD não definidos")
        return None

    existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()

    if existing:
        print("✅ Admin já existe")
        return existing

    try:
        user = User(
            email=ADMIN_EMAIL,
            password=hash_password(ADMIN_PASSWORD),
            role="ADMIN",
            is_verified=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        student = Student(
            user_id=user.id,
            nome="Admin",
            telefone="",
            modalidade="Muay-Thai",
            graduacao="Branca",
            status="ativo",
        )

        db.add(student)
        db.commit()

        print("🔥 Admin criado com sucesso!")

        return user

    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar admin: {e}")
        return None