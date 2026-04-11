from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.feed import FeedComment, FeedItem, FeedLike
from app.schemas.feed import (
    FeedCommentCreate,
    FeedItemCreate,
    FeedItemUpdate,
)
from app.models.feed import now_utc


class FeedService:
    def __init__(self, db: Session):
        self.db = db

    def create_item(
        self, data: FeedItemCreate, created_by_user_id: int, gym_id: int
    ) -> FeedItem:
        item = FeedItem(
            gym_id=gym_id,
            created_by=created_by_user_id,
            tipo=data.tipo,
            titulo=data.titulo,
            descricao=data.descricao,
            evento_data=data.evento_data,
            local=data.local,
            modalidade=data.modalidade,
            graduacao=data.graduacao,
            imagem_link=data.imagem_link,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_item(self, item: FeedItem, data: FeedItemUpdate) -> FeedItem:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return item

        for field, value in update_data.items():
            setattr(item, field, value)

        item.updated_at = now_utc()
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_item_or_none(
        self, item_id: int, gym_id: Optional[int] = None
    ) -> Optional[FeedItem]:
        q = self.db.query(FeedItem).filter(FeedItem.id == item_id)
        if gym_id is not None:
            q = q.filter(FeedItem.gym_id == gym_id)
        return q.first()

    def like_item(self, item_id: int, user_id: int) -> bool:
        existing = (
            self.db.query(FeedLike)
            .filter(FeedLike.feed_item_id == item_id, FeedLike.user_id == user_id)
            .first()
        )
        if existing:
            return False

        like = FeedLike(feed_item_id=item_id, user_id=user_id)
        self.db.add(like)
        self.db.commit()
        return True

    def unlike_item(self, item_id: int, user_id: int) -> bool:
        existing = (
            self.db.query(FeedLike)
            .filter(FeedLike.feed_item_id == item_id, FeedLike.user_id == user_id)
            .first()
        )
        if not existing:
            return False

        self.db.delete(existing)
        self.db.commit()
        return True

    def add_comment(
        self, item_id: int, user_id: int, data: FeedCommentCreate
    ) -> FeedComment:
        comment = FeedComment(feed_item_id=item_id, user_id=user_id, conteudo=data.conteudo)
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def _counts_for_ids(self, ids: List[int]) -> Tuple[Dict[int, int], Dict[int, int]]:
        if not ids:
            return {}, {}

        like_rows = (
            self.db.query(FeedLike.feed_item_id, func.count(FeedLike.id))
            .filter(FeedLike.feed_item_id.in_(ids))
            .group_by(FeedLike.feed_item_id)
            .all()
        )
        comment_rows = (
            self.db.query(FeedComment.feed_item_id, func.count(FeedComment.id))
            .filter(FeedComment.feed_item_id.in_(ids))
            .group_by(FeedComment.feed_item_id)
            .all()
        )

        like_map = {item_id: count for item_id, count in like_rows}
        comment_map = {item_id: count for item_id, count in comment_rows}
        return like_map, comment_map

    def list_feed(
        self,
        gym_id: int,
        limit: int = 50,
        offset: int = 0,
        liked_by_me_user_id: Optional[int] = None,
    ):
        items = (
            self.db.query(FeedItem)
            .filter(FeedItem.gym_id == gym_id)
            .order_by(FeedItem.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        ids = [i.id for i in items]
        like_map, comment_map = self._counts_for_ids(ids)

        liked_set: Set[int] = set()
        if liked_by_me_user_id is not None and ids:
            rows = (
                self.db.query(FeedLike.feed_item_id)
                .filter(
                    FeedLike.user_id == liked_by_me_user_id,
                    FeedLike.feed_item_id.in_(ids),
                )
                .all()
            )
            liked_set = {r[0] for r in rows}

        result = []
        for item in items:
            result.append(
                {
                    "id": item.id,
                    "created_by": item.created_by,
                    "tipo": item.tipo,
                    "titulo": item.titulo,
                    "descricao": item.descricao,
                    "evento_data": item.evento_data,
                    "local": item.local,
                    "modalidade": item.modalidade,
                    "graduacao": item.graduacao,
                    "image_url": item.image_url,
                    "imagem_link": item.imagem_link,
                    "like_count": like_map.get(item.id, 0),
                    "comment_count": comment_map.get(item.id, 0),
                    "liked_by_me": (
                        (item.id in liked_set) if liked_by_me_user_id is not None else None
                    ),
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
            )
        return result

    def list_comments(self, item_id: int) -> List[FeedComment]:
        return (
            self.db.query(FeedComment)
            .filter(FeedComment.feed_item_id == item_id)
            .order_by(FeedComment.created_at.asc())
            .all()
        )

    def get_like_count(self, item_id: int) -> int:
        return (
            self.db.query(func.count(FeedLike.id))
            .filter(FeedLike.feed_item_id == item_id)
            .scalar()
        )

    def get_comment_count(self, item_id: int) -> int:
        return (
            self.db.query(func.count(FeedComment.id))
            .filter(FeedComment.feed_item_id == item_id)
            .scalar()
        )

