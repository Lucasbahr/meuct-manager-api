from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password
from app.models.student import Student
import os
from dotenv import load_dotenv

db = SessionLocal()

load_dotenv()
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()

if existing:
    print("Admin já existe")
else:
    user = User(
        email=ADMIN_EMAIL,
        password=hash_password(ADMIN_PASSWORD),
        role="ADMIN",
        is_verified=True,
    )

    db.add(user)

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

    print("Admin criado com sucesso!")
