"""Chamadas HTTP aos provedores (pagamento direto na conta da academia)."""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException

from app.models.marketplace import OrderItem, ShopOrder
from app.services.payment_credentials import ProviderCredentials

PAYPAL_API_BASE = os.getenv("PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")
MERCADOPAGO_API = "https://api.mercadopago.com"

# Token de credencial da *aplicação* (painel) costuma usar o prefixo APP_USR sem par
# refresh_token OAuth. Com refresh_token gravado, o mesmo prefixo pode vir na resposta
# oficial do OAuth do vendedor — nesse caso o checkout é válido.
MERCADOPAGO_APPLICATION_ACCESS_PREFIX = "APP_USR"


def mercadopago_bearer_for_vendor_api(creds: ProviderCredentials) -> str:
    """
    Bearer para preference / payments: exige access_token e rejeita credencial de aplicação
    isolada (APP_USR sem refresh_token OAuth armazenado).
    """
    if not creds.access_token or not str(creds.access_token).strip():
        raise HTTPException(
            status_code=400,
            detail="Mercado Pago não configurado (sem access_token OAuth do vendedor)",
        )
    tok = str(creds.access_token).strip()
    rt = (creds.refresh_token or "").strip()
    if (
        tok.upper().startswith(MERCADOPAGO_APPLICATION_ACCESS_PREFIX)
        and not rt
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Mercado Pago: access_token APP_USR sem refresh_token indica token da "
                "aplicação, incompatível com checkout. Conecte via OAuth em "
                "/payment/mercado-pago/oauth/start."
            ),
        )
    return tok


def _paypal_oauth(creds: ProviderCredentials) -> str:
    if not creds.client_id or not creds.client_secret:
        raise HTTPException(
            status_code=400,
            detail="PayPal: configure client_id e client_secret da academia",
        )
    with httpx.Client(timeout=45.0) as client:
        r = client.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            auth=(creds.client_id, creds.client_secret),
            headers={
                "Accept": "application/json",
                "Accept-Language": "en_US",
            },
            data={"grant_type": "client_credentials"},
        )
        if r.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"PayPal OAuth falhou: {r.status_code} {r.text[:500]}",
            )
        return r.json()["access_token"]


def _paypal_checkout_approval_href(data: dict) -> str | None:
    """Orders v2: fluxo atual usa `payer-action`; respostas antigas traziam `approve`."""
    links = data.get("links") or []
    for rel in ("payer-action", "approve"):
        for link in links:
            if link.get("rel") == rel:
                href = link.get("href")
                if isinstance(href, str) and href.startswith("http"):
                    return href
    return None


def paypal_create_checkout(
    creds: ProviderCredentials,
    order: ShopOrder,
    return_url: str,
    cancel_url: str,
) -> tuple[str, str]:
    """Retorna (url de checkout no navegador, paypal_order_id).

    Modelo atual da Orders API: `payment_source.paypal.experience_context`
    (substitui `application_context`, hoje marcado como deprecated).
    """
    access = _paypal_oauth(creds)
    total = format(Decimal(str(order.total_amount)), "f")
    body: dict[str, Any] = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": str(order.id),
                "custom_id": str(order.id),
                "description": f"Pedido #{order.id}",
                "amount": {
                    "currency_code": "BRL",
                    "value": total,
                },
            }
        ],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                    "user_action": "PAY_NOW",
                    "shipping_preference": "NO_SHIPPING",
                }
            }
        },
    }
    with httpx.Client(timeout=45.0) as client:
        r = client.post(
            f"{PAYPAL_API_BASE}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {access}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        if r.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail=f"PayPal criar ordem falhou: {r.status_code} {r.text[:500]}",
            )
        data = r.json()
        order_id = data["id"]
        href = _paypal_checkout_approval_href(data)
        if not href:
            raise HTTPException(
                status_code=502,
                detail="PayPal não retornou link de aprovação (payer-action/approve)",
            )
        return href, order_id


def mercadopago_create_preference(
    creds: ProviderCredentials,
    order: ShopOrder,
    items: list[OrderItem],
    return_url: str,
    cancel_url: str,
    *,
    gym_id: int,
) -> tuple[str, str]:
    """Retorna (init_point, preference_id). Usa access_token da conta do vendedor (Checkout Pro)."""
    token = mercadopago_bearer_for_vendor_api(creds)
    mp_items = []
    for oi in items:
        title = oi.product.name if oi.product else f"Produto {oi.product_id}"
        mp_items.append(
            {
                "title": title[:256],
                "quantity": oi.quantity,
                "unit_price": float(oi.price),
                "currency_id": "BRL",
            }
        )
    body: dict[str, Any] = {
        "items": mp_items,
        "external_reference": str(order.id),
        "metadata": {"order_id": str(order.id), "gym_id": str(gym_id)},
        "back_urls": {
            "success": return_url,
            "failure": cancel_url,
            "pending": return_url,
        },
        "auto_return": "approved",
    }
    base = os.getenv("BASE_URL", "").strip().rstrip("/")
    if base:
        body["notification_url"] = f"{base}/webhooks/mercado-pago/{gym_id}"
    with httpx.Client(timeout=45.0) as client:
        r = client.post(
            f"{MERCADOPAGO_API}/checkout/preferences",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        if r.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail=f"Mercado Pago preference falhou: {r.status_code} {r.text[:500]}",
            )
        data = r.json()
        pref_id = data.get("id")
        url = data.get("init_point") or data.get("sandbox_init_point")
        if not pref_id or not url:
            raise HTTPException(
                status_code=502,
                detail="Mercado Pago não retornou init_point / sandbox_init_point",
            )
        return str(url), str(pref_id)


def mercadopago_fetch_payment(creds: ProviderCredentials, payment_id: str) -> dict:
    token = mercadopago_bearer_for_vendor_api(creds)
    with httpx.Client(timeout=30.0) as client:
        r = client.get(
            f"{MERCADOPAGO_API}/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Mercado Pago GET payment falhou: {r.status_code}",
            )
        return r.json()


def mercadopago_oauth_exchange_code(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    *,
    test_token: bool = False,
) -> dict[str, Any]:
    """Troca o authorization code por tokens da conta do vendedor (OAuth MP)."""
    json_body: dict[str, Any] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    if test_token:
        json_body["test_token"] = "true"
    with httpx.Client(timeout=45.0) as client:
        r = client.post(
            f"{MERCADOPAGO_API}/oauth/token",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=json_body,
        )
    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Mercado Pago OAuth token falhou: {r.status_code} {r.text[:500]}",
        )
    return r.json()


def mercadopago_oauth_refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    *,
    test_token: bool = False,
) -> dict[str, Any]:
    """Renova access_token usando refresh_token (OAuth conta vendedor)."""
    json_body: dict[str, Any] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    if test_token:
        json_body["test_token"] = "true"
    with httpx.Client(timeout=45.0) as client:
        r = client.post(
            f"{MERCADOPAGO_API}/oauth/token",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=json_body,
        )
    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Mercado Pago refresh token falhou: {r.status_code} {r.text[:500]}",
        )
    return r.json()
