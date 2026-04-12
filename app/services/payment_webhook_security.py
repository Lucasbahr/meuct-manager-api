"""Validação de webhooks PayPal e Mercado Pago (assinatura / API oficial)."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Mapping

import httpx
from fastapi import HTTPException, Request


def strict_payment_webhooks() -> bool:
    v = os.getenv("STRICT_PAYMENT_WEBHOOKS", "true").strip().lower()
    return v in ("1", "true", "yes")


def _paypal_headers_map(request: Request) -> dict[str, str]:
    return {k.lower(): v for k, v in request.headers.items()}


def _verify_paypal_webhook_sync(headers: Mapping[str, str], body: dict[str, Any]) -> None:
    webhook_id = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()
    client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    base = os.getenv("PAYPAL_API_BASE", "https://api-m.paypal.com").strip().rstrip("/")

    if not (webhook_id and client_id and client_secret):
        raise HTTPException(
            status_code=503,
            detail="PayPal: defina PAYPAL_WEBHOOK_ID, PAYPAL_CLIENT_ID e PAYPAL_CLIENT_SECRET para validar webhooks",
        )

    tid = headers.get("paypal-transmission-id")
    ttime = headers.get("paypal-transmission-time")
    cert_url = headers.get("paypal-cert-url")
    auth_algo = headers.get("paypal-auth-algo")
    sig = headers.get("paypal-transmission-sig")
    if not all([tid, ttime, cert_url, auth_algo, sig]):
        raise HTTPException(status_code=403, detail="Cabeçalhos de assinatura PayPal ausentes")

    with httpx.Client(timeout=25.0) as client:
        token_r = client.post(
            f"{base}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={
                "Accept": "application/json",
                "Accept-Language": "en_US",
            },
        )
        if token_r.status_code >= 400:
            raise HTTPException(
                status_code=503,
                detail="Falha ao obter token OAuth do PayPal para validação",
            )
        access_token = token_r.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=503, detail="Resposta OAuth PayPal inválida")

        verify_payload = {
            "transmission_id": tid,
            "transmission_time": ttime,
            "cert_url": cert_url,
            "auth_algo": auth_algo,
            "transmission_sig": sig,
            "webhook_id": webhook_id,
            "webhook_event": body,
        }
        vr = client.post(
            f"{base}/v1/notifications/verify-webhook-signature",
            json=verify_payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        if vr.status_code >= 400:
            raise HTTPException(status_code=403, detail="Falha na validação do webhook PayPal")

        status = (vr.json() or {}).get("verification_status")
        if status != "SUCCESS":
            raise HTTPException(status_code=403, detail="Assinatura do webhook PayPal inválida")


def require_paypal_webhook_verified(request: Request, body: dict[str, Any]) -> None:
    if not strict_payment_webhooks():
        return
    hdr = _paypal_headers_map(request)
    _verify_paypal_webhook_sync(hdr, body)


def _parse_mp_x_signature(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    ts, v1 = None, None
    for part in value.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if k == "ts":
            ts = v
        elif k == "v1":
            v1 = v
    return ts, v1


def _mercadopago_data_id(request: Request, body: dict[str, Any]) -> str | None:
    q = request.query_params.get("data.id")
    if q is not None and str(q).strip() != "":
        return str(q).strip()
    data = body.get("data")
    if isinstance(data, dict) and data.get("id") is not None:
        return str(data["id"]).strip()
    if body.get("id") is not None:
        return str(body["id"]).strip()
    return None


def require_mercadopago_webhook_verified(request: Request, body: dict[str, Any]) -> None:
    if not strict_payment_webhooks():
        return

    secret = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Mercado Pago: defina MERCADOPAGO_WEBHOOK_SECRET para validar webhooks",
        )

    x_sig = request.headers.get("x-signature")
    req_id = request.headers.get("x-request-id")
    ts, v1 = _parse_mp_x_signature(x_sig)
    data_id = _mercadopago_data_id(request, body)

    if not ts or not v1 or not req_id or not data_id:
        raise HTTPException(
            status_code=403,
            detail="Assinatura Mercado Pago: dados insuficientes (x-signature, x-request-id ou id)",
        )

    manifest = f"id:{data_id};request-id:{req_id};ts:{ts};"
    expected = hmac.new(
        secret.encode("utf-8"),
        manifest.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, v1):
        raise HTTPException(status_code=403, detail="Assinatura do webhook Mercado Pago inválida")
