from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.session import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class FeedItem(Base):
    __tablename__ = "feed_items"

    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    tipo = Column(String(32), nullable=False)  # "luta" | "evento" | "graduacao"
    titulo = Column(String(128), nullable=False)
    descricao = Column(Text, nullable=True)

    evento_data = Column(Date, nullable=True)
    local = Column(String(128), nullable=True)

    modalidade = Column(String(64), nullable=True)
    graduacao = Column(String(64), nullable=True)

    image_path = Column(String(512), nullable=True)  # storage object key
    # URL externa ao tocar na imagem (app admin).
    imagem_link = Column(String(1024), nullable=True)

    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def image_url(self) -> Optional[str]:
        if not self.image_path or self.id is None:
            return None
        return f"/feed/{self.id}/photo"


class FeedLike(Base):
    __tablename__ = "feed_likes"

    id = Column(Integer, primary_key=True, index=True)
    feed_item_id = Column(Integer, ForeignKey("feed_items.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    __table_args__ = (
        UniqueConstraint("feed_item_id", "user_id", name="uq_feed_like_item_user"),
    )


class FeedComment(Base):
    __tablename__ = "feed_comments"

    id = Column(Integer, primary_key=True, index=True)
    feed_item_id = Column(Integer, ForeignKey("feed_items.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conteudo = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

