"""Conta Mercado Pago OAuth por usuário (academia); tokens cifrados com PAYMENT_CREDENTIALS_FERNET_KEY quando definida."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


def now_utc():
    return datetime.now(timezone.utc)


class MercadoPagoAccount(Base):
    __tablename__ = "mercadopago_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_mercadopago_accounts_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_in = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc
    )

    user = relationship("User", back_populates="mercadopago_account")
