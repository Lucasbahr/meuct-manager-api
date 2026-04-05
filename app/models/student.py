from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Date
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

    e_atleta = Column(Boolean, default=False, nullable=False)
    cartel_mma = Column(String(128), nullable=True)
    cartel_jiu = Column(String(128), nullable=True)
    cartel_k1 = Column(String(128), nullable=True)
    nivel_competicao = Column(String(32), nullable=True)
    link_tapology = Column(String(512), nullable=True)

    data_nascimento = Column(Date, nullable=True)
    ultima_luta_em = Column(Date, nullable=True)
    ultima_luta_modalidade = Column(String(64), nullable=True)
    foto_path = Column(String(512), nullable=True)
    # Foto só para o cartão na aba Atletas (admin envia; independente da foto de perfil).
    foto_atleta_path = Column(String(512), nullable=True)

    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def email(self):
        return self.user.email if self.user else None

    @property
    def foto_url(self):
        if not self.foto_path or self.id is None:
            return None
        return f"/students/{self.id}/photo"

    @property
    def foto_atleta_url(self):
        if not self.foto_atleta_path or self.id is None:
            return None
        return f"/students/{self.id}/athlete-card/photo"
