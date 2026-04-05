from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from jose import JWTError, jwt
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.core.security import ALGORITHM, SECRET_KEY
from app.db.deps import get_db
from app.schemas.response import ResponseBase
from app.models.feed import FeedItem
from app.schemas.feed import (
    FeedCommentCreate,
    FeedCommentResponse,
    FeedItemCreate,
    FeedItemResponse,
    FeedItemUpdate,
    FeedLikeResponse,
)
from app.services.feed_service import FeedService
from app.services.student_photo import get_photo_bytes, save_feed_photo, delete_feed_photo
from datetime import datetime, timezone

router = APIRouter(prefix="/feed", tags=["Feed"])


def optional_current_user(request: Request) -> Optional[dict]:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


@router.get("/", response_model=ResponseBase)
def list_feed(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    user = optional_current_user(request)
    liked_by_me_user_id = user["user_id"] if user else None

    service = FeedService(db)
    items = service.list_feed(
        limit=max(1, min(limit, 200)),
        offset=max(0, offset),
        liked_by_me_user_id=liked_by_me_user_id,
    )

    return {
        "success": True,
        "message": "Feed carregado",
        "data": [FeedItemResponse.model_validate(x) for x in items],
    }


@router.get("/{item_id}", response_model=ResponseBase)
def get_feed_item(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = optional_current_user(request)
    liked_by_me_user_id = user["user_id"] if user else None

    service = FeedService(db)
    item = service.get_item_or_none(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feed item not found")

    like_count = service.get_like_count(item_id)
    comment_count = service.get_comment_count(item_id)

    liked = None
    if liked_by_me_user_id is not None:
        from app.models.feed import FeedLike

        liked = (
            db.query(FeedLike)
            .filter(
                FeedLike.feed_item_id == item_id,
                FeedLike.user_id == liked_by_me_user_id,
            )
            .first()
            is not None
        )

    return {
        "success": True,
        "message": "Item carregado",
        "data": FeedItemResponse.model_validate(
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
                "like_count": like_count,
                "comment_count": comment_count,
                "liked_by_me": liked,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
        ),
    }


@router.post("/", response_model=ResponseBase)
def create_feed_item(
    data: FeedItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    service = FeedService(db)
    item = service.create_item(data, created_by_user_id=current_user["user_id"])
    return {
        "success": True,
        "message": "Feed item criado",
        "data": FeedItemResponse.model_validate(
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
                "like_count": 0,
                "comment_count": 0,
                "liked_by_me": None,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
        ),
    }


@router.put("/{item_id}", response_model=ResponseBase)
def update_feed_item(
    item_id: int,
    data: FeedItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    service = FeedService(db)
    item = service.get_item_or_none(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feed item not found")
    item = service.update_item(item, data)
    return {
        "success": True,
        "message": "Feed item atualizado",
        "data": FeedItemResponse.model_validate(
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
                "like_count": service.get_like_count(item_id),
                "comment_count": service.get_comment_count(item_id),
                "liked_by_me": None,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
        ),
    }


@router.post("/{item_id}/likes", response_model=ResponseBase)
def like_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FeedService(db)
    item = service.get_item_or_none(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feed item not found")

    service.like_item(item_id=item_id, user_id=current_user["user_id"])
    like_count = service.get_like_count(item_id)
    return {
        "success": True,
        "message": "Curtida registrada",
        "data": FeedLikeResponse(liked=True, like_count=like_count),
    }


@router.delete("/{item_id}/likes", response_model=ResponseBase)
def unlike_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FeedService(db)
    service.unlike_item(item_id=item_id, user_id=current_user["user_id"])
    like_count = service.get_like_count(item_id)
    return {
        "success": True,
        "message": "Curtida removida",
        "data": FeedLikeResponse(liked=False, like_count=like_count),
    }


@router.get("/{item_id}/comments", response_model=ResponseBase)
def list_comments(
    item_id: int,
    db: Session = Depends(get_db),
):
    service = FeedService(db)
    comments = service.list_comments(item_id)
    return {
        "success": True,
        "message": "Comentários carregados",
        "data": [FeedCommentResponse.model_validate(c) for c in comments],
    }


@router.post("/{item_id}/comments", response_model=ResponseBase)
def add_comment(
    item_id: int,
    data: FeedCommentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FeedService(db)
    item = service.get_item_or_none(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feed item not found")

    comment = service.add_comment(item_id=item_id, user_id=current_user["user_id"], data=data)
    return {
        "success": True,
        "message": "Comentário criado",
        "data": FeedCommentResponse.model_validate(comment),
    }


@router.post("/{item_id}/photo", response_model=ResponseBase)
async def admin_upload_feed_photo(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    service = FeedService(db)
    item = service.get_item_or_none(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feed item not found")

    content = await file.read()
    old = item.image_path
    item.image_path = save_feed_photo(item_id, content, file.content_type or "")
    delete_feed_photo(old)
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return {
        "success": True,
        "message": "Foto do feed atualizada",
        "data": {"image_url": item.image_url},
    }


@router.get("/{item_id}/photo")
def get_feed_photo(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = db.query(FeedItem).filter(FeedItem.id == item_id).first()
    if not item or not item.image_path:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    content, media_type = get_photo_bytes(item.image_path)
    return Response(content=content, media_type=media_type)

