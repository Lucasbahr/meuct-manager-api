"""Configuração de features por tenant (academia = gym)."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.session import Base


class TenantConfig(Base):
    __tablename__ = "tenant_configs"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(
        Integer,
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    permite_checkin = Column(Boolean, nullable=False, default=True)
    permite_agendamento = Column(Boolean, nullable=False, default=False)
    mostrar_ranking = Column(Boolean, nullable=False, default=True)
    mostrar_graduacao = Column(Boolean, nullable=False, default=True)
    cobrar_mensalidade = Column(Boolean, nullable=False, default=False)

    gym = relationship("Gym", back_populates="tenant_config")
