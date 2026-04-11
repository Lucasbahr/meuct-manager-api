from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_academy_admin, require_gym_id
from app.db.deps import get_db
from app.models.marketplace import Product
from app.schemas.response import ResponseBase
from app.schemas.stock import StockAddRequest, StockRemoveRequest
from app.services import stock_service as stock_svc

router = APIRouter(tags=["Stock"])


@router.post("/stock/add", response_model=ResponseBase)
def stock_add(
    body: StockAddRequest,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    m = stock_svc.add_stock(db, gym_id, body.product_id, body.quantity)
    db.commit()
    return {
        "success": True,
        "message": "Entrada de estoque registrada",
        "data": {
            "movement_id": m.id,
            "product_id": m.product_id,
            "quantity": m.quantity,
            "movement_type": m.movement_type,
        },
    }


@router.post("/stock/remove", response_model=ResponseBase)
def stock_remove(
    body: StockRemoveRequest,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    m = stock_svc.remove_stock(
        db,
        gym_id,
        body.product_id,
        body.quantity,
        body.reason,
    )
    db.commit()
    return {
        "success": True,
        "message": "Saída de estoque registrada",
        "data": {
            "movement_id": m.id,
            "product_id": m.product_id,
            "quantity": m.quantity,
            "movement_type": m.movement_type,
            "reason": m.reason,
        },
    }


@router.get("/stock/movements", response_model=ResponseBase)
def stock_movements_history(
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
    product_id: Optional[int] = Query(None),
    movement_type: Optional[Literal["IN", "OUT"]] = Query(None),
    reason: Optional[str] = Query(None),
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None),
    sort: Literal["asc", "desc"] = Query("desc"),
):
    data = stock_svc.list_movements(
        db,
        gym_id,
        product_id=product_id,
        movement_type=movement_type,
        reason=reason,
        created_from=created_from,
        created_to=created_to,
        sort_desc=(sort == "desc"),
    )
    return {
        "success": True,
        "message": "Histórico de movimentos",
        "data": data,
    }


@router.get("/stock/{product_id}", response_model=ResponseBase)
def stock_get_product(
    product_id: int,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
    movements_limit: int = Query(50, ge=0, le=500),
):
    p = (
        db.query(Product)
        .filter(Product.id == product_id, Product.gym_id == gym_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    qty = stock_svc.get_stock(db, p)
    movements = []
    if movements_limit > 0:
        movements = stock_svc.list_movements(
            db,
            gym_id,
            product_id=product_id,
            sort_desc=True,
            limit=movements_limit,
        )

    return {
        "success": True,
        "message": "Estoque do produto",
        "data": {
            "product_id": p.id,
            "name": p.name,
            "track_stock": p.track_stock,
            "quantity": qty,
            "movements": movements,
        },
    }


@router.get("/notifications", response_model=ResponseBase)
def list_gym_notifications(
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
    unread_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
):
    data = stock_svc.list_notifications(
        db, gym_id, unread_only=unread_only, limit=limit
    )
    return {
        "success": True,
        "message": "Notificações",
        "data": data,
    }


@router.patch("/notifications/{notification_id}/read", response_model=ResponseBase)
def mark_notification_read_route(
    notification_id: int,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    stock_svc.mark_notification_read(db, gym_id, notification_id)
    db.commit()
    return {"success": True, "message": "Marcada como lida", "data": None}
