from html import escape
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import require_academy_admin
from app.db.deps import get_db
from app.schemas.mercadopago_user import PaymentPreferenceCreate
from app.schemas.response import ResponseBase
from app.services import mercadopago_account_service as mp_user

router = APIRouter(tags=["Mercado Pago (usuário)"])


@router.get("/mercadopago/connect", response_model=ResponseBase)
def mercadopago_user_connect(
    next_url: Optional[str] = Query(
        None,
        description="Opcional: redirect após OAuth (exige MP_OAUTH_SUCCESS_URL_PREFIX)",
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


@router.get("/mercadopago/callback")
def mercadopago_user_callback(
    db: Session = Depends(get_db),
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """Callback público do Mercado Pago; associa tokens ao usuário indicado em `state`."""
    oauth_err = error or error_description
    result = mp_user.mercadopago_user_oauth_handle_callback(db, code, state, oauth_err)
    db.commit()
    if result.get("redirect"):
        return RedirectResponse(result["redirect"], status_code=302)
    if result["ok"]:
        return HTMLResponse(
            "<html><head><meta charset='utf-8'></head><body>"
            "Mercado Pago conectado à sua conta. Você pode fechar esta aba."
            "</body></html>"
        )
    return HTMLResponse(
        f"<html><body>Erro: {escape(result['message'])}</body></html>",
        status_code=400,
    )


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
