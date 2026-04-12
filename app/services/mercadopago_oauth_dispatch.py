"""Callback OAuth Mercado Pago da academia: grava tokens em gym_payment_settings."""

from __future__ import annotations

from html import escape
from typing import Any

from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.services import marketplace_service as msvc


def dispatch_mercadopago_oauth_callback(
    db: Session,
    code: str | None,
    state: str | None,
    oauth_err: str | None,
) -> dict[str, Any]:
    """Troca `code` por tokens e persiste em `GymPaymentSettings` (provedor mercado_pago)."""
    return msvc.mercadopago_oauth_handle_callback(db, code, state, oauth_err)


def mercadopago_oauth_callback_http_response(result: dict[str, Any]) -> Response:
    if result.get("redirect"):
        return RedirectResponse(result["redirect"], status_code=302)
    if result["ok"]:
        return HTMLResponse(
            "<html><head><meta charset='utf-8'></head><body>"
            "Mercado Pago conectado à academia. Você pode fechar esta aba."
            "</body></html>"
        )
    return HTMLResponse(
        f"<html><body>Erro: {escape(result['message'])}</body></html>",
        status_code=400,
    )
