from html import escape
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_academy_admin, require_gym_id
from app.core.roles import is_staff
from app.db.deps import get_db
from app.schemas.marketplace import (
    CategoryCreate,
    CheckoutRequest,
    MercadoPagoOAuthStart,
    OrderCreate,
    PaymentConfigCreate,
    ProductCreate,
    ProductUpdate,
    SubcategoryCreate,
)
from app.schemas.response import ResponseBase
from app.services import marketplace_service as msvc

router = APIRouter(tags=["Marketplace"])


# --- Retorno do checkout no mobile (navegador externo) ---


@router.get("/payment/mobile-return", response_class=HTMLResponse)
def payment_mobile_return():
    """Após pagamento aprovado (PayPal / Mercado Pago); o app abre em navegador externo."""
    return HTMLResponse(
        "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        "<title>Pagamento</title></head><body style='font-family:system-ui;padding:24px;"
        "background:#121212;color:#eee;text-align:center'>"
        "<p style='font-size:18px'>Pagamento concluído.</p>"
        "<p style='opacity:.75'>Feche esta aba e volte ao aplicativo.</p></body></html>"
    )


@router.get("/payment/mobile-cancel", response_class=HTMLResponse)
def payment_mobile_cancel():
    """Usuário cancelou no fluxo do provedor."""
    return HTMLResponse(
        "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        "<title>Pagamento</title></head><body style='font-family:system-ui;padding:24px;"
        "background:#121212;color:#eee;text-align:center'>"
        "<p style='font-size:18px'>Pagamento cancelado.</p>"
        "<p style='opacity:.75'>Feche esta aba e volte ao aplicativo.</p></body></html>"
    )


# --- Admin (academia / sistema na academia) ---


@router.post("/products", response_model=ResponseBase)
def admin_create_product(
    body: ProductCreate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    p = msvc.create_product(
        db,
        gym_id,
        name=body.name,
        description=body.description,
        price=body.price,
        stock=body.stock,
        track_stock=body.track_stock,
        is_active=body.is_active,
        category_id=body.category_id,
        subcategory_id=body.subcategory_id,
        image_urls=body.image_urls,
    )
    db.commit()
    return {
        "success": True,
        "message": "Produto criado",
        "data": msvc.get_product(db, gym_id, p.id, allow_inactive=True),
    }


@router.put("/products/{product_id}", response_model=ResponseBase)
def admin_update_product(
    product_id: int,
    body: ProductUpdate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    msvc.update_product(
        db,
        gym_id,
        product_id,
        name=body.name,
        description=body.description,
        price=body.price,
        stock=body.stock,
        is_active=body.is_active,
        category_id=body.category_id,
        subcategory_id=body.subcategory_id,
        image_urls=body.image_urls,
    )
    db.commit()
    return {
        "success": True,
        "message": "Produto atualizado",
        "data": msvc.get_product(db, gym_id, product_id, allow_inactive=True),
    }


@router.post("/categories", response_model=ResponseBase)
def admin_create_category(
    body: CategoryCreate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    c = msvc.create_category(db, gym_id, body.name)
    db.commit()
    return {
        "success": True,
        "message": "Categoria criada",
        "data": {"id": c.id, "gym_id": c.gym_id, "name": c.name},
    }


@router.post("/subcategories", response_model=ResponseBase)
def admin_create_subcategory(
    body: SubcategoryCreate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    s = msvc.create_subcategory(db, gym_id, body.category_id, body.name)
    db.commit()
    return {
        "success": True,
        "message": "Subcategoria criada",
        "data": {"id": s.id, "category_id": s.category_id, "name": s.name},
    }


@router.post("/payment/config", response_model=ResponseBase)
def admin_payment_config(
    body: PaymentConfigCreate,
    _admin=Depends(require_academy_admin),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    row = msvc.upsert_payment_settings(
        db,
        gym_id,
        provider=body.provider,
        client_id=body.client_id,
        client_secret=body.client_secret,
        access_token=body.access_token,
        refresh_token=body.refresh_token,
        public_key=body.public_key,
    )
    db.commit()
    return {
        "success": True,
        "message": "Configuração de pagamento salva",
        "data": msvc.payment_settings_to_out(row),
    }


@router.post("/payment/mercado-pago/oauth/start", response_model=ResponseBase)
def mercadopago_oauth_start(
    body: MercadoPagoOAuthStart = MercadoPagoOAuthStart(),
    _admin=Depends(require_academy_admin),
    gym_id: int = Depends(require_gym_id),
):
    next_u = str(body.next_url) if body.next_url else None
    url = msvc.mercadopago_oauth_authorization_url(gym_id, next_u)
    return {
        "success": True,
        "message": "Abra authorization_url no navegador para conectar o Mercado Pago",
        "data": {"authorization_url": url},
    }


@router.get("/payment/mercado-pago/oauth/callback")
def mercadopago_oauth_callback(
    db: Session = Depends(get_db),
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    oauth_err = error or error_description
    result = msvc.mercadopago_oauth_handle_callback(db, code, state, oauth_err)
    db.commit()
    if result.get("redirect"):
        return RedirectResponse(result["redirect"], status_code=302)
    if result["ok"]:
        return HTMLResponse(
            "<html><body>Mercado Pago conectado à academia. Você pode fechar esta aba.</body></html>"
        )
    return HTMLResponse(
        f"<html><body>Erro: {escape(result['message'])}</body></html>",
        status_code=400,
    )


# --- Aluno / catálogo ---


@router.get("/products", response_model=ResponseBase)
def list_products(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
    category_id: Optional[int] = Query(None),
    subcategory_id: Optional[int] = Query(None),
    sort: Literal["name", "price", "created_at"] = Query("created_at"),
    order: Literal["asc", "desc"] = Query("desc"),
):
    active_only = not is_staff(user.get("role"))
    data = msvc.list_products(
        db,
        gym_id,
        active_only=active_only,
        category_id=category_id,
        sort_field=sort,
        sort_dir=order,
    )
    if subcategory_id is not None:
        data = [p for p in data if p.get("subcategory_id") == subcategory_id]
    return {
        "success": True,
        "message": "Produtos",
        "data": data,
    }


@router.get("/products/{product_id}", response_model=ResponseBase)
def get_product_detail(
    product_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    allow_inactive = is_staff(user.get("role"))
    data = msvc.get_product(db, gym_id, product_id, allow_inactive=allow_inactive)
    return {
        "success": True,
        "message": "Produto",
        "data": data,
    }


# --- Pedidos / checkout ---


@router.post("/orders", response_model=ResponseBase)
def create_order_route(
    body: OrderCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    st = msvc.get_student_in_gym(db, user["user_id"], gym_id)
    raw_items = [i.model_dump() for i in body.items]
    o = msvc.create_order(db, gym_id, st.id, raw_items)
    db.commit()
    db.refresh(o)
    o = msvc.get_order_for_student(db, o.id, st.id, gym_id)
    return {
        "success": True,
        "message": "Pedido criado",
        "data": msvc.order_to_dict(o),
    }


@router.post("/orders/{order_id}/checkout", response_model=ResponseBase)
def checkout_route(
    order_id: int,
    body: CheckoutRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    st = msvc.get_student_in_gym(db, user["user_id"], gym_id)
    data = msvc.checkout_order(
        db,
        order_id,
        st.id,
        gym_id,
        body.provider,
        str(body.return_url),
        str(body.cancel_url),
    )
    db.commit()
    return {
        "success": True,
        "message": "Redirecione o cliente para concluir o pagamento",
        "data": data,
    }


# --- Webhooks (URL com gym_id para saber qual conta consultar) ---


@router.post("/webhooks/paypal/{gym_id}")
async def webhook_paypal(gym_id: int, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    result = msvc.handle_paypal_webhook(db, gym_id, body)
    db.commit()
    return result


@router.post("/webhooks/mercado-pago/{gym_id}")
async def webhook_mercado_pago(
    gym_id: int, request: Request, db: Session = Depends(get_db)
):
    body = await request.json()
    result = msvc.handle_mercadopago_webhook(db, gym_id, body)
    db.commit()
    return result
