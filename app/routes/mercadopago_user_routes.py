from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_academy_admin
from app.db.deps import get_db
from app.schemas.mercadopago_user import PaymentPreferenceCreate
from app.schemas.response import ResponseBase
from app.services import mercadopago_account_service as mp_user
from app.services.mercadopago_oauth_dispatch import (
    dispatch_mercadopago_oauth_callback,
    mercadopago_oauth_callback_http_response,
)

router = APIRouter(tags=["Mercado Pago (usuário)"])


@router.get("/mercadopago/connect", response_model=ResponseBase)
def mercadopago_user_connect(
    next_url: Optional[str] = Query(
        None,
        description="Opcional: redirect após OAuth (exige MERCADOPAGO_OAUTH_SUCCESS_URL_PREFIX)",
    ),
    user=Depends(require_academy_admin),
):
    """URL de autorização OAuth (abrir no navegador / WebView). Tokens não são expostos."""
    uid = int(user["user_id"])
    url = mp_user.mercadopago_user_authorization_url(uid, next_url)
    return {
        "success": True,
        "message": "Abra url no navegador para conectar o Mercado Pago",
        "data": {"url": url},
    }


@router.get("/mercadopago/status", response_model=ResponseBase)
def mercadopago_user_link_status(
    user=Depends(require_academy_admin),
    db: Session = Depends(get_db),
):
    """Indica se o admin logado já concluiu OAuth (conta MP por usuário)."""
    uid = int(user["user_id"])
    row = mp_user.get_mercadopago_account(db, uid)
    token = (row.access_token or "").strip() if row is not None else ""
    linked = bool(row) and bool(token)
    return {
        "success": True,
        "message": "OK",
        "data": {
            "has_access_token": linked,
            "connected": linked,
            "oauth_flow": "mp_user_oauth",
        },
    }


@router.get("/mercadopago/callback")
def mercadopago_user_callback(
    db: Session = Depends(get_db),
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """Callback OAuth MP: fluxo por usuário ou loja (mesmo redirect_uri, `state` diferencia)."""
    oauth_err = error or error_description
    result, flow = dispatch_mercadopago_oauth_callback(db, code, state, oauth_err)
    db.commit()
    return mercadopago_oauth_callback_http_response(result, flow)


@router.post("/payments/create", response_model=ResponseBase)
def payments_create_preference(
    body: PaymentPreferenceCreate,
    user=Depends(require_academy_admin),
    db: Session = Depends(get_db),
):
    """Cria preference no Mercado Pago com o access_token da conta OAuth do usuário logado."""
    uid = int(user["user_id"])
    init_point = mp_user.create_preference_for_logged_user(
        db,
        uid,
        title=body.title,
        quantity=body.quantity,
        unit_price=body.unit_price,
    )
    db.commit()
    return {
        "success": True,
        "message": "Redirecione o pagador para init_point",
        "data": {"init_point": init_point},
    }
