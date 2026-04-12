<<<<<<< HEAD
"""Callback OAuth Mercado Pago da academia: grava tokens em gym_payment_settings."""
=======
"""Dispatch do callback OAuth MP: fluxo por usuário (`mp_user_oauth`) ou loja por academia (`mp_oauth`).

Permite uma única MERCADOPAGO_OAUTH_REDIRECT_URI (ex.: /mercadopago/callback) registrada no painel MP
para ambos os fluxos, desde que o `state` identifique o tipo.
"""
>>>>>>> b1dbeab8d479e5f7aac15d541cde409808b66298

from __future__ import annotations

from html import escape
<<<<<<< HEAD
from typing import Any
=======
from typing import Any, Literal, Optional
>>>>>>> b1dbeab8d479e5f7aac15d541cde409808b66298

from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

<<<<<<< HEAD
from app.services import marketplace_service as msvc
=======
from app.core.security import decode_mercadopago_user_oauth_state
from app.services import marketplace_service as msvc
from app.services import mercadopago_account_service as mp_user
>>>>>>> b1dbeab8d479e5f7aac15d541cde409808b66298


def dispatch_mercadopago_oauth_callback(
    db: Session,
<<<<<<< HEAD
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
=======
    code: Optional[str],
    state: Optional[str],
    oauth_err: Optional[str],
) -> tuple[dict[str, Any], Literal["user", "gym"]]:
    if state:
        try:
            decode_mercadopago_user_oauth_state(state)
            return (
                mp_user.mercadopago_user_oauth_handle_callback(
                    db, code, state, oauth_err
                ),
                "user",
            )
        except ValueError:
            pass
    return (
        msvc.mercadopago_oauth_handle_callback(db, code, state, oauth_err),
        "gym",
    )


def mercadopago_oauth_callback_http_response(
    result: dict[str, Any], flow: Literal["user", "gym"]
) -> Response:
    if result.get("redirect"):
        return RedirectResponse(result["redirect"], status_code=302)
    if result["ok"]:
        msg = (
            "Mercado Pago conectado à sua conta. Você pode fechar esta aba."
            if flow == "user"
            else "Mercado Pago conectado à academia. Você pode fechar esta aba."
        )
        return HTMLResponse(
            "<html><head><meta charset='utf-8'></head><body>"
            f"{msg}</body></html>"
>>>>>>> b1dbeab8d479e5f7aac15d541cde409808b66298
        )
    return HTMLResponse(
        f"<html><body>Erro: {escape(result['message'])}</body></html>",
        status_code=400,
    )
