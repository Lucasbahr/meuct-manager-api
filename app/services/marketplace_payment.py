"""Chamadas HTTP aos provedores (pagamento direto na conta da academia)."""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException

from app.models.marketplace import GymPaymentSettings, OrderItem, ShopOrder

PAYPAL_API_BASE = os.getenv("PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")
MERCADOPAGO_API = "https://api.mercadopago.com"


def _paypal_oauth(settings: GymPaymentSettings) -> str:
    if not settings.client_id or not settings.client_secret:
        raise HTTPException(
            status_code=400,
            detail="PayPal: configure client_id e client_secret da academia",
        )
    with httpx.Client(timeout=45.0) as client:
        r = client.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            auth=(settings.client_id, settings.client_secret),
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


def paypal_create_checkout(
    settings: GymPaymentSettings,
    order: ShopOrder,
    return_url: str,
    cancel_url: str,
) -> tuple[str, str]:
    """Retorna (approval_url, paypal_order_id)."""
    access = _paypal_oauth(settings)
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
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW",
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
        approve = next(
            (l for l in data.get("links", []) if l.get("rel") == "approve"),
            None,
        )
        if not approve or not approve.get("href"):
            raise HTTPException(
                status_code=502,
                detail="PayPal não retornou link de aprovação",
            )
        return approve["href"], order_id


def mercadopago_create_preference(
    settings: GymPaymentSettings,
    order: ShopOrder,
    items: list[OrderItem],
    return_url: str,
    cancel_url: str,
) -> tuple[str, str]:
    """Retorna (init_point, preference_id). Usa access_token da conta do vendedor."""
    if not settings.access_token:
        raise HTTPException(
            status_code=400,
            detail="Mercado Pago: configure access_token da academia",
        )
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
    body = {
        "items": mp_items,
        "external_reference": str(order.id),
        "back_urls": {
            "success": return_url,
            "failure": cancel_url,
            "pending": return_url,
        },
        "auto_return": "approved",
    }
    with httpx.Client(timeout=45.0) as client:
        r = client.post(
            f"{MERCADOPAGO_API}/checkout/preferences",
            headers={
                "Authorization": f"Bearer {settings.access_token}",
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
                detail="Mercado Pago não retornou init_point",
            )
        return url, pref_id


def mercadopago_fetch_payment(settings: GymPaymentSettings, payment_id: str) -> dict:
    if not settings.access_token:
        raise HTTPException(status_code=400, detail="Mercado Pago não configurado")
    with httpx.Client(timeout=30.0) as client:
        r = client.get(
            f"{MERCADOPAGO_API}/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {settings.access_token}"},
        )
        if r.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Mercado Pago GET payment falhou: {r.status_code}",
            )
        return r.json()
