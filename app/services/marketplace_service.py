from __future__ import annotations

import os
from collections import defaultdict
from decimal import Decimal
from typing import Any, List, Optional
from urllib.parse import quote, urlencode

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.marketplace import (
    GymPaymentSettings,
    OrderItem,
    Product,
    ProductCategory,
    ProductImage,
    ProductSubcategory,
    ShopOrder,
)
from app.models.student import Student
from app.models.user import User
from app.core import payment_credentials_crypto as pcc
from app.core.security import (
    create_mercadopago_oauth_state,
    decode_mercadopago_oauth_state,
)
from app.services import marketplace_payment as pay
from app.services.payment_credentials import decrypt_row as payment_decrypt_row
from app.services import commission_service as commission_svc
from app.services import stock_service as stock_svc

ORDER_PENDING = "pending"
ORDER_AWAITING = "awaiting_payment"
ORDER_PAID = "paid"
ORDER_CANCELLED = "cancelled"

PROVIDER_PAYPAL = "paypal"
PROVIDER_MERCADOPAGO = "mercado_pago"


def get_student_in_gym(db: Session, user_id: int, gym_id: int) -> Student:
    st = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.user_id == user_id, User.gym_id == gym_id)
        .first()
    )
    if not st:
        raise HTTPException(
            status_code=400,
            detail="Perfil de aluno não encontrado nesta academia",
        )
    return st


def _validate_category_subcategory(
    db: Session,
    gym_id: int,
    category_id: Optional[int],
    subcategory_id: Optional[int],
) -> None:
    if category_id is None and subcategory_id is None:
        return
    if subcategory_id is not None and category_id is None:
        raise HTTPException(
            status_code=400,
            detail="subcategory_id exige category_id",
        )
    if category_id is not None:
        cat = (
            db.query(ProductCategory)
            .filter(
                ProductCategory.id == category_id,
                ProductCategory.gym_id == gym_id,
            )
            .first()
        )
        if not cat:
            raise HTTPException(status_code=404, detail="Categoria não encontrada")
    if subcategory_id is not None:
        sub = (
            db.query(ProductSubcategory)
            .join(ProductCategory)
            .filter(
                ProductSubcategory.id == subcategory_id,
                ProductCategory.gym_id == gym_id,
            )
            .first()
        )
        if not sub:
            raise HTTPException(status_code=404, detail="Subcategoria não encontrada")
        if category_id is not None and sub.category_id != category_id:
            raise HTTPException(
                status_code=400,
                detail="Subcategoria não pertence à categoria informada",
            )


def _product_base_query(db: Session, gym_id: int):
    return (
        db.query(Product)
        .options(
            joinedload(Product.category),
            joinedload(Product.subcategory),
            joinedload(Product.images),
        )
        .filter(Product.gym_id == gym_id)
    )


def product_to_dict(db: Session, p: Product) -> dict[str, Any]:
    if p.track_stock:
        stock_svc.sync_stock_cache(db, p)
    return {
        "id": p.id,
        "gym_id": p.gym_id,
        "name": p.name,
        "description": p.description,
        "price": p.price,
        "stock": p.stock if p.track_stock else None,
        "track_stock": p.track_stock,
        "is_active": p.is_active,
        "category_id": p.category_id,
        "subcategory_id": p.subcategory_id,
        "category_name": p.category.name if p.category else None,
        "subcategory_name": p.subcategory.name if p.subcategory else None,
        "images": [
            {"id": i.id, "image_url": i.image_url, "sort_order": i.sort_order}
            for i in sorted(p.images, key=lambda x: x.sort_order)
        ],
    }


def create_product(
    db: Session,
    gym_id: int,
    *,
    name: str,
    description: Optional[str],
    price: Decimal,
    stock: int,
    track_stock: bool,
    is_active: bool,
    category_id: Optional[int],
    subcategory_id: Optional[int],
    image_urls: List[str],
) -> Product:
    _validate_category_subcategory(db, gym_id, category_id, subcategory_id)
    p = Product(
        gym_id=gym_id,
        name=name,
        description=description,
        price=price,
        stock=0,
        track_stock=track_stock,
        is_active=is_active,
        category_id=category_id,
        subcategory_id=subcategory_id,
    )
    db.add(p)
    db.flush()
    for idx, url in enumerate(image_urls):
        db.add(
            ProductImage(product_id=p.id, image_url=url.strip(), sort_order=idx)
        )
    db.flush()
    if track_stock and stock > 0:
        stock_svc.seed_initial_purchase(db, gym_id, p.id, stock)
    else:
        stock_svc.sync_stock_cache(db, p)
    db.flush()
    db.refresh(p)
    return p


def update_product(
    db: Session,
    gym_id: int,
    product_id: int,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[Decimal] = None,
    stock: Optional[int] = None,
    is_active: Optional[bool] = None,
    category_id: Optional[int] = None,
    subcategory_id: Optional[int] = None,
    image_urls: Optional[List[str]] = None,
) -> Product:
    p = (
        _product_base_query(db, gym_id)
        .filter(Product.id == product_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    new_cat = category_id if category_id is not None else p.category_id
    new_sub = subcategory_id if subcategory_id is not None else p.subcategory_id
    _validate_category_subcategory(db, gym_id, new_cat, new_sub)

    if name is not None:
        p.name = name
    if description is not None:
        p.description = description
    if price is not None:
        p.price = price
    if stock is not None:
        if not p.track_stock:
            raise HTTPException(
                status_code=400,
                detail="Produto sem rastreamento: não é possível definir estoque numérico",
            )
        stock_svc.reconcile_stock_target(db, gym_id, product_id, stock)
    if is_active is not None:
        p.is_active = is_active
    if category_id is not None:
        p.category_id = category_id
    if subcategory_id is not None:
        p.subcategory_id = subcategory_id

    if image_urls is not None:
        db.query(ProductImage).filter(ProductImage.product_id == p.id).delete(
            synchronize_session=False
        )
        for idx, url in enumerate(image_urls):
            db.add(
                ProductImage(
                    product_id=p.id, image_url=url.strip(), sort_order=idx
                )
            )

    db.flush()
    db.refresh(p)
    stock_svc.sync_stock_cache(db, p)
    return p


def list_products(
    db: Session,
    gym_id: int,
    *,
    active_only: bool,
    category_id: Optional[int],
    sort_field: str,
    sort_dir: str,
) -> List[dict[str, Any]]:
    q = _product_base_query(db, gym_id)
    if active_only:
        q = q.filter(Product.is_active.is_(True))
    if category_id is not None:
        q = q.filter(Product.category_id == category_id)

    col = getattr(Product, sort_field, None)
    if col is None:
        col = Product.created_at
    order_expr = col.asc() if sort_dir == "asc" else col.desc()
    rows = q.order_by(order_expr).all()
    return [product_to_dict(db, p) for p in rows]


def get_product(
    db: Session,
    gym_id: int,
    product_id: int,
    *,
    allow_inactive: bool,
) -> dict[str, Any]:
    p = (
        _product_base_query(db, gym_id)
        .filter(Product.id == product_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if not allow_inactive and not p.is_active:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product_to_dict(db, p)


def create_category(db: Session, gym_id: int, name: str) -> ProductCategory:
    c = ProductCategory(gym_id=gym_id, name=name.strip())
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def create_subcategory(
    db: Session, gym_id: int, category_id: int, name: str
) -> ProductSubcategory:
    cat = (
        db.query(ProductCategory)
        .filter(
            ProductCategory.id == category_id,
            ProductCategory.gym_id == gym_id,
        )
        .first()
    )
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    s = ProductSubcategory(category_id=category_id, name=name.strip())
    db.add(s)
    db.flush()
    db.refresh(s)
    return s


def get_payment_settings_row(
    db: Session, gym_id: int, provider: str
) -> Optional[GymPaymentSettings]:
    if provider not in (PROVIDER_PAYPAL, PROVIDER_MERCADOPAGO):
        raise HTTPException(status_code=400, detail="provider inválido")
    return (
        db.query(GymPaymentSettings)
        .filter(
            GymPaymentSettings.gym_id == gym_id,
            GymPaymentSettings.provider == provider,
        )
        .first()
    )


def upsert_payment_settings(
    db: Session,
    gym_id: int,
    *,
    provider: str,
    client_id: Optional[str],
    client_secret: Optional[str],
    access_token: Optional[str],
    refresh_token: Optional[str],
    public_key: Optional[str] = None,
) -> GymPaymentSettings:
    if provider not in (PROVIDER_PAYPAL, PROVIDER_MERCADOPAGO):
        raise HTTPException(status_code=400, detail="provider inválido")

    if provider == PROVIDER_MERCADOPAGO and access_token is not None:
        at = str(access_token).strip()
        if at:
            rt = str(refresh_token).strip() if refresh_token is not None else ""
            if not rt:
                if at.upper().startswith(pay.MERCADOPAGO_APPLICATION_ACCESS_PREFIX):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Mercado Pago: token APP_USR sem refresh_token indica credencial "
                            "da aplicação. Use o fluxo OAuth ou informe access_token e "
                            "refresh_token retornados pelo /oauth/token."
                        ),
                    )
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Mercado Pago: informe refresh_token junto com access_token "
                        "(ambos vêm da resposta do OAuth)."
                    ),
                )

    row = (
        db.query(GymPaymentSettings)
        .filter(
            GymPaymentSettings.gym_id == gym_id,
            GymPaymentSettings.provider == provider,
        )
        .first()
    )
    if not row:
        row = GymPaymentSettings(gym_id=gym_id, provider=provider)
        db.add(row)

    if client_id is not None:
        row.client_id = pcc.encrypt_credential(client_id)
    if client_secret is not None:
        row.client_secret = pcc.encrypt_credential(client_secret)
    if access_token is not None:
        row.access_token = pcc.encrypt_credential(access_token)
    if refresh_token is not None:
        row.refresh_token = pcc.encrypt_credential(refresh_token)
    if public_key is not None:
        row.public_key = public_key.strip() if public_key else None

    db.flush()
    db.refresh(row)
    return row


def payment_settings_to_out(row: GymPaymentSettings) -> dict[str, Any]:
    return {
        "id": row.id,
        "gym_id": row.gym_id,
        "provider": row.provider,
        "client_id_hint": pcc.mask_credential_suffix(row.client_id),
        "credentials_encrypted_at_rest": pcc.fernet_key_configured(),
        "has_client_secret": bool(row.client_secret),
        "has_access_token": bool(row.access_token),
        "has_refresh_token": bool(row.refresh_token),
        "has_public_key": bool(row.public_key),
    }


def create_order(
    db: Session,
    gym_id: int,
    student_id: int,
    items: List[dict],
) -> ShopOrder:
    if not items:
        raise HTTPException(status_code=400, detail="Itens obrigatórios")

    merged: dict[int, int] = defaultdict(int)
    for raw in items:
        merged[int(raw["product_id"])] += int(raw["quantity"])

    total = Decimal("0")
    resolved: list[tuple[Product, int]] = []

    for pid, qty in merged.items():
        p = (
            db.query(Product)
            .filter(Product.id == pid, Product.gym_id == gym_id)
            .first()
        )
        if not p:
            raise HTTPException(
                status_code=404,
                detail=f"Produto {pid} não encontrado nesta academia",
            )
        if not p.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Produto {p.name} inativo",
            )
        if p.track_stock:
            available = stock_svc.computed_quantity(db, p.id)
            if available < qty:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para {p.name}",
                )
        line = Decimal(str(p.price)) * qty
        total += line
        resolved.append((p, qty))

    order = ShopOrder(
        gym_id=gym_id,
        student_id=student_id,
        total_amount=total,
        status=ORDER_PENDING,
    )
    db.add(order)
    db.flush()

    for p, qty in resolved:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=p.id,
                quantity=qty,
                price=p.price,
            )
        )

    db.flush()
    db.refresh(order)
    return order


def order_to_dict(order: ShopOrder) -> dict[str, Any]:
    return {
        "id": order.id,
        "gym_id": order.gym_id,
        "student_id": order.student_id,
        "total_amount": order.total_amount,
        "status": order.status,
        "payment_provider": order.payment_provider,
        "external_checkout_id": order.external_checkout_id,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": [
            {
                "id": it.id,
                "product_id": it.product_id,
                "quantity": it.quantity,
                "price": it.price,
            }
            for it in order.items
        ],
    }


def get_order_for_student(
    db: Session, order_id: int, student_id: int, gym_id: int
) -> ShopOrder:
    o = (
        db.query(ShopOrder)
        .options(joinedload(ShopOrder.items).joinedload(OrderItem.product))
        .filter(
            ShopOrder.id == order_id,
            ShopOrder.student_id == student_id,
            ShopOrder.gym_id == gym_id,
        )
        .first()
    )
    if not o:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return o


def checkout_order(
    db: Session,
    order_id: int,
    student_id: int,
    gym_id: int,
    provider: str,
    return_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    if provider not in (PROVIDER_PAYPAL, PROVIDER_MERCADOPAGO):
        raise HTTPException(status_code=400, detail="provider inválido")

    order = get_order_for_student(db, order_id, student_id, gym_id)
    if order.status != ORDER_PENDING:
        raise HTTPException(
            status_code=400,
            detail="Pedido já iniciado ou finalizado",
        )

    settings = (
        db.query(GymPaymentSettings)
        .filter(
            GymPaymentSettings.gym_id == gym_id,
            GymPaymentSettings.provider == provider,
        )
        .first()
    )
    if not settings:
        raise HTTPException(
            status_code=400,
            detail="Academia não configurou este meio de pagamento",
        )

    creds = payment_decrypt_row(settings)
    if provider == PROVIDER_PAYPAL:
        url, ext_id = pay.paypal_create_checkout(
            creds, order, return_url, cancel_url
        )
    else:
        items = list(order.items)
        for it in items:
            if it.product is None:
                db.refresh(it, ["product"])
        url, ext_id = pay.mercadopago_create_preference(
            creds, order, items, return_url, cancel_url, gym_id=gym_id
        )

    order.payment_provider = provider
    order.external_checkout_id = ext_id
    order.status = ORDER_AWAITING
    db.flush()
    db.refresh(order)

    return {
        "provider": provider,
        "redirect_url": url,
        "external_checkout_id": ext_id,
    }


def mark_order_paid(db: Session, order: ShopOrder) -> bool:
    if order.status == ORDER_PAID:
        return False
    if order.status not in (ORDER_PENDING, ORDER_AWAITING):
        raise HTTPException(status_code=400, detail="Estado do pedido inválido")

    for it in order.items:
        p = db.query(Product).filter(Product.id == it.product_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Produto do pedido não existe")
        if p.track_stock:
            available = stock_svc.computed_quantity(db, p.id)
            if available < it.quantity:
                raise HTTPException(status_code=409, detail="Estoque insuficiente")

    stock_svc.on_payment_approved(db, order)
    order.status = ORDER_PAID
    db.flush()
    commission_svc.ensure_commission_for_paid_order(db, order)
    db.flush()
    return True


def handle_paypal_webhook(db: Session, gym_id: int, body: dict) -> dict[str, Any]:
    event_type = body.get("event_type")
    resource = body.get("resource") or {}

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        custom_id = resource.get("custom_id")
        if not custom_id:
            return {"ok": True, "ignored": True, "reason": "sem custom_id"}
        try:
            oid = int(custom_id)
        except (TypeError, ValueError):
            return {"ok": True, "ignored": True, "reason": "custom_id inválido"}

        order = (
            db.query(ShopOrder)
            .options(joinedload(ShopOrder.items))
            .filter(
                ShopOrder.id == oid,
                ShopOrder.gym_id == gym_id,
                ShopOrder.payment_provider == PROVIDER_PAYPAL,
            )
            .first()
        )
        if not order:
            return {"ok": True, "ignored": True, "reason": "pedido não encontrado"}

        try:
            changed = mark_order_paid(db, order)
        except HTTPException as e:
            return {"ok": False, "detail": e.detail}
        return {"ok": True, "paid": changed, "order_id": order.id}

    return {"ok": True, "ignored": True, "event_type": event_type}


def handle_mercadopago_webhook(
    db: Session, gym_id: int, body: dict
) -> dict[str, Any]:
    payment_id = None
    if isinstance(body.get("data"), dict):
        payment_id = body["data"].get("id")
    if payment_id is None:
        payment_id = body.get("id") or body.get("data_id")

    if payment_id is None:
        return {"ok": True, "ignored": True, "reason": "sem payment id"}

    settings = (
        db.query(GymPaymentSettings)
        .filter(
            GymPaymentSettings.gym_id == gym_id,
            GymPaymentSettings.provider == PROVIDER_MERCADOPAGO,
        )
        .first()
    )
    if not settings:
        return {"ok": False, "error": "Mercado Pago não configurado"}

    pid = str(payment_id)
    creds = payment_decrypt_row(settings)
    data = pay.mercadopago_fetch_payment(creds, pid)
    if data.get("status") != "approved":
        return {"ok": True, "ignored": True, "status": data.get("status")}

    ext_ref = data.get("external_reference")
    if not ext_ref:
        return {"ok": True, "ignored": True, "reason": "sem external_reference"}
    try:
        oid = int(ext_ref)
    except (TypeError, ValueError):
        return {"ok": True, "ignored": True}

    order = (
        db.query(ShopOrder)
        .options(joinedload(ShopOrder.items))
        .filter(
            ShopOrder.id == oid,
            ShopOrder.gym_id == gym_id,
        )
        .first()
    )
    if not order:
        return {"ok": True, "ignored": True, "reason": "pedido não encontrado"}

    try:
        changed = mark_order_paid(db, order)
    except HTTPException as e:
        return {"ok": False, "detail": e.detail}
    return {"ok": True, "paid": changed, "order_id": order.id}


def _validate_mercadopago_oauth_next_url(next_url: Optional[str]) -> None:
    if not next_url:
        return
    prefix = os.getenv("MERCADOPAGO_OAUTH_SUCCESS_URL_PREFIX", "").strip()
    if not prefix:
        raise HTTPException(
            status_code=400,
            detail=(
                "Para usar next_url, defina MERCADOPAGO_OAUTH_SUCCESS_URL_PREFIX "
                "(ex.: https://app.suaempresa.com)."
            ),
        )
    if not next_url.startswith(prefix):
        raise HTTPException(
            status_code=400,
            detail="next_url deve começar com MERCADOPAGO_OAUTH_SUCCESS_URL_PREFIX",
        )


def _mercadopago_oauth_redirect_failure(
    next_url: Optional[str], message: str
) -> Optional[str]:
    if not next_url:
        return None
    q = quote(message[:500], safe="")
    sep = "&" if "?" in next_url else "?"
    return f"{next_url}{sep}mp_oauth=error&mp_oauth_msg={q}"


def _mercadopago_oauth_redirect_success(next_url: Optional[str]) -> Optional[str]:
    if not next_url:
        return None
    sep = "&" if "?" in next_url else "?"
    return f"{next_url}{sep}mp_oauth=ok"


def mercadopago_oauth_authorization_url(
    gym_id: int,
    next_url: Optional[str] = None,
) -> str:
    """
    URL para o admin abrir no navegador e autorizar a conta Mercado Pago da academia.
    Credenciais da *aplicação* ficam em env (não são da academia).
    """
    client_id = os.getenv("MERCADOPAGO_OAUTH_CLIENT_ID", "").strip()
    redirect_uri = os.getenv("MERCADOPAGO_OAUTH_REDIRECT_URI", "").strip()
    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=503,
            detail=(
                "Mercado Pago OAuth não configurado no servidor. "
                "Defina MERCADOPAGO_OAUTH_CLIENT_ID e MERCADOPAGO_OAUTH_REDIRECT_URI."
            ),
        )
    _validate_mercadopago_oauth_next_url(next_url)
    try:
        state = create_mercadopago_oauth_state(gym_id, next_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    auth_base = os.getenv(
        "MERCADOPAGO_OAUTH_AUTH_BASE", "https://auth.mercadopago.com"
    ).rstrip("/")
    params = {
        "client_id": client_id,
        "response_type": "code",
        "platform_id": "mp",
        "state": state,
        "redirect_uri": redirect_uri,
    }
    return f"{auth_base}/authorization?{urlencode(params)}"


def mercadopago_oauth_handle_callback(
    db: Session,
    code: Optional[str],
    state: Optional[str],
    oauth_error: Optional[str],
) -> dict[str, Any]:
    """Troca o code por tokens e grava em GymPaymentSettings (mercado_pago)."""
    next_url: Optional[str] = None
    if state:
        try:
            decoded_early = decode_mercadopago_oauth_state(state)
            next_url = decoded_early.get("next")
        except ValueError:
            next_url = None

    if oauth_error:
        msg = oauth_error
        return {
            "ok": False,
            "message": msg,
            "redirect": _mercadopago_oauth_redirect_failure(next_url, msg),
        }

    if not code or not state:
        msg = "Parâmetros code ou state ausentes"
        return {
            "ok": False,
            "message": msg,
            "redirect": _mercadopago_oauth_redirect_failure(next_url, msg),
        }

    try:
        decoded = decode_mercadopago_oauth_state(state)
        next_url = decoded.get("next")
        gym_id = decoded["gym_id"]
    except ValueError as e:
        return {
            "ok": False,
            "message": str(e),
            "redirect": None,
        }

    client_id = os.getenv("MERCADOPAGO_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("MERCADOPAGO_OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("MERCADOPAGO_OAUTH_REDIRECT_URI", "").strip()
    if not client_id or not client_secret or not redirect_uri:
        msg = "Servidor sem credenciais OAuth do Mercado Pago configuradas"
        return {
            "ok": False,
            "message": msg,
            "redirect": _mercadopago_oauth_redirect_failure(next_url, msg),
        }

    test_token = os.getenv("MERCADOPAGO_OAUTH_TEST_TOKEN", "").lower() in (
        "1",
        "true",
        "yes",
    )
    try:
        data = pay.mercadopago_oauth_exchange_code(
            client_id,
            client_secret,
            code,
            redirect_uri,
            test_token=test_token,
        )
    except HTTPException as he:
        detail = he.detail
        msg = detail if isinstance(detail, str) else "Falha ao obter token do Mercado Pago"
        return {
            "ok": False,
            "message": msg,
            "redirect": _mercadopago_oauth_redirect_failure(next_url, msg),
        }

    access = data.get("access_token")
    refresh = data.get("refresh_token")
    uid = data.get("user_id")
    if not access:
        msg = "Resposta do Mercado Pago sem access_token"
        return {
            "ok": False,
            "message": msg,
            "redirect": _mercadopago_oauth_redirect_failure(next_url, msg),
        }
    if uid is None:
        msg = "Resposta do Mercado Pago sem user_id"
        return {
            "ok": False,
            "message": msg,
            "redirect": _mercadopago_oauth_redirect_failure(next_url, msg),
        }
    if not refresh or not str(refresh).strip():
        msg = "Resposta do Mercado Pago sem refresh_token"
        return {
            "ok": False,
            "message": msg,
            "redirect": _mercadopago_oauth_redirect_failure(next_url, msg),
        }
    upsert_payment_settings(
        db,
        gym_id,
        provider=PROVIDER_MERCADOPAGO,
        client_id=str(uid),
        client_secret=None,
        access_token=str(access),
        refresh_token=str(refresh).strip(),
    )
    return {
        "ok": True,
        "message": "",
        "redirect": _mercadopago_oauth_redirect_success(next_url),
    }
