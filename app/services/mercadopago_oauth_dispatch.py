"""Dispatch do callback OAuth MP: fluxo por usuário (`mp_user_oauth`) ou loja por academia (`mp_oauth`).

Permite uma única MERCADOPAGO_OAUTH_REDIRECT_URI (ex.: /mercadopago/callback) registrada no painel MP
para ambos os fluxos, desde que o `state` identifique o tipo.
"""

from __future__ import annotations

from html import escape
from typing import Any, Literal, Optional

from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.security import decode_mercadopago_user_oauth_state
from app.services import marketplace_service as msvc
from app.services import mercadopago_account_service as mp_user


def dispatch_mercadopago_oauth_callback(
    db: Session,
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
        )
    return HTMLResponse(
        f"<html><body>Erro: {escape(result['message'])}</body></html>",
        status_code=400,
    )
