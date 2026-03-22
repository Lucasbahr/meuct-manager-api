from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime, timezone
from app.db.session import Base
from sqlalchemy.orm import relationship


def now_utc():
    return datetime.now(timezone.utc)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    user = relationship("User")

    nome = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    endereco = Column(String, nullable=True)

    modalidade = Column(String, default="Muay-Thai")
    graduacao = Column(String, default="Branca")
    tempo_de_treino = Column(Integer, nullable=True)
    status = Column(String, default="ativo")

    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def email(self):
        return self.user.email if self.user else None
