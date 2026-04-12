"""OAuth Mercado Pago por usuário (conta do vendedor) + preferences Checkout Pro."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote, urlencode

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core import payment_credentials_crypto as pcc
from app.core.security import (
    create_mercadopago_user_oauth_state,
    decode_mercadopago_user_oauth_state,
)
from app.models.mercadopago_account import MercadoPagoAccount
from app.services import marketplace_payment as pay


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _mp_oauth_test_token() -> bool:
    raw = (
        os.getenv("MP_OAUTH_TEST_TOKEN", "").strip()
        or os.getenv("MERCADOPAGO_OAUTH_TEST_TOKEN", "").strip()
    )
    return raw.lower() in ("1", "true", "yes")


def mp_user_oauth_app_config() -> tuple[str, str, str]:
    client_id = os.getenv("MP_CLIENT_ID", "").strip()
    client_secret = os.getenv("MP_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("MP_REDIRECT_URI", "").strip()
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(
            status_code=503,
            detail=(
                "Mercado Pago OAuth (usuário) não configurado. "
                "Defina MP_CLIENT_ID, MP_CLIENT_SECRET e MP_REDIRECT_URI."
            ),
        )
    return client_id, client_secret, redirect_uri


def _validate_user_oauth_next_url(next_url: Optional[str]) -> None:
    if not next_url:
        return
    prefix = os.getenv("MP_OAUTH_SUCCESS_URL_PREFIX", "").strip()
    if not prefix:
        raise HTTPException(
            status_code=400,
            detail=(
                "Para usar next_url, defina MP_OAUTH_SUCCESS_URL_PREFIX "
                "(ex.: https://app.suaempresa.com)."
            ),
        )
    if not next_url.startswith(prefix):
        raise HTTPException(
            status_code=400,
            detail="next_url deve começar com MP_OAUTH_SUCCESS_URL_PREFIX",
        )


def user_oauth_redirect_failure(
    next_url: Optional[str], message: str
) -> Optional[str]:
    if not next_url:
        return None
    q = quote(message[:500], safe="")
    sep = "&" if "?" in next_url else "?"
    return f"{next_url}{sep}mp_user_oauth=error&mp_user_oauth_msg={q}"


def user_oauth_redirect_success(next_url: Optional[str]) -> Optional[str]:
    if not next_url:
        return None
    sep = "&" if "?" in next_url else "?"
    return f"{next_url}{sep}mp_user_oauth=ok"


def mercadopago_user_authorization_url(
    user_id: int,
    next_url: Optional[str] = None,
) -> str:
    client_id, _, redirect_uri = mp_user_oauth_app_config()
    _validate_user_oauth_next_url(next_url)
    try:
        state = create_mercadopago_user_oauth_state(user_id, next_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    auth_base = os.getenv(
        "MP_OAUTH_AUTH_BASE", "https://auth.mercadopago.com.br"
    ).rstrip("/")
    params = {
        "client_id": client_id,
        "response_type": "code",
        "platform_id": "mp",
        "state": state,
        "redirect_uri": redirect_uri,
    }
    return f"{auth_base}/authorization?{urlencode(params)}"


def _apply_token_payload_to_account(
    row: MercadoPagoAccount,
    data: dict[str, Any],
) -> None:
    access = data.get("access_token")
    if not access or not isinstance(access, str):
        raise ValueError("Resposta do Mercado Pago sem access_token")
    refresh = data.get("refresh_token")
    expires = data.get("expires_in")
    try:
        expires_in = int(expires) if expires is not None else 21_600
    except (TypeError, ValueError):
        expires_in = 21_600
    row.access_token = pcc.encrypt_credential(access) or access
    row.refresh_token = (
        pcc.encrypt_credential(refresh) if refresh else row.refresh_token
    )
    row.expires_in = expires_in
    row.updated_at = _now()


def mercadopago_user_oauth_handle_callback(
    db: Session,
    code: Optional[str],
    state: Optional[str],
    oauth_error: Optional[str],
) -> dict[str, Any]:
    next_url: Optional[str] = None
    if state:
        try:
            decoded_early = decode_mercadopago_user_oauth_state(state)
            next_url = decoded_early.get("next")
        except ValueError:
            next_url = None

    if oauth_error:
        msg = str(oauth_error)
        return {
            "ok": False,
            "message": msg,
            "redirect": user_oauth_redirect_failure(next_url, msg),
        }

    if not code or not state:
        msg = "Parâmetros code ou state ausentes"
        return {
            "ok": False,
            "message": msg,
            "redirect": user_oauth_redirect_failure(next_url, msg),
        }

    try:
        decoded = decode_mercadopago_user_oauth_state(state)
        next_url = decoded.get("next")
        uid = decoded["user_id"]
    except ValueError as e:
        return {"ok": False, "message": str(e), "redirect": None}

    try:
        client_id, client_secret, redirect_uri = mp_user_oauth_app_config()
    except HTTPException:
        msg = "Servidor sem MP_CLIENT_ID / MP_CLIENT_SECRET / MP_REDIRECT_URI"
        return {
            "ok": False,
            "message": msg,
            "redirect": user_oauth_redirect_failure(next_url, msg),
        }

    try:
        data = pay.mercadopago_oauth_exchange_code(
            client_id,
            client_secret,
            code,
            redirect_uri,
            test_token=_mp_oauth_test_token(),
        )
    except HTTPException as he:
        detail = he.detail
        msg = detail if isinstance(detail, str) else "Falha ao obter token do Mercado Pago"
        return {
            "ok": False,
            "message": msg,
            "redirect": user_oauth_redirect_failure(next_url, msg),
        }

    try:
        row = db.query(MercadoPagoAccount).filter(MercadoPagoAccount.user_id == uid).first()
        if row is None:
            row = MercadoPagoAccount(user_id=uid, access_token="", expires_in=0)
            db.add(row)
            db.flush()
        _apply_token_payload_to_account(row, data)
    except ValueError as e:
        msg = str(e)
        return {
            "ok": False,
            "message": msg,
            "redirect": user_oauth_redirect_failure(next_url, msg),
        }

    return {
        "ok": True,
        "message": "",
        "redirect": user_oauth_redirect_success(next_url),
    }


def get_mercadopago_account(db: Session, user_id: int) -> Optional[MercadoPagoAccount]:
    return (
        db.query(MercadoPagoAccount)
        .filter(MercadoPagoAccount.user_id == user_id)
        .first()
    )


def _access_likely_expired(account: MercadoPagoAccount) -> bool:
    buffer = timedelta(seconds=90)
    ttl_sec = max(int(account.expires_in or 0), 300)
    updated = _as_utc_aware(account.updated_at)
    return _now() >= updated + timedelta(seconds=ttl_sec) - buffer


def ensure_user_mercadopago_access_token(db: Session, account: MercadoPagoAccount) -> str:
    """Devolve access_token em claro; renova com refresh_token quando necessário."""
    plain = pcc.decrypt_credential(account.access_token)
    if not plain:
        raise HTTPException(
            status_code=400,
            detail="Conta Mercado Pago inválida; conecte novamente em /mercadopago/connect",
        )
    if not _access_likely_expired(account):
        return plain

    refresh_plain = pcc.decrypt_credential(account.refresh_token)
    if not refresh_plain:
        return plain

    client_id, client_secret, _ = mp_user_oauth_app_config()
    try:
        data = pay.mercadopago_oauth_refresh_access_token(
            client_id,
            client_secret,
            refresh_plain,
            test_token=_mp_oauth_test_token(),
        )
    except HTTPException:
        return plain

    try:
        _apply_token_payload_to_account(account, data)
    except ValueError:
        return plain
    db.add(account)
    new_plain = pcc.decrypt_credential(account.access_token)
    if not new_plain:
        raise HTTPException(
            status_code=502,
            detail="Falha ao atualizar token Mercado Pago após refresh",
        )
    return new_plain


def create_preference_for_logged_user(
    db: Session,
    user_id: int,
    *,
    title: str,
    quantity: int,
    unit_price: float,
) -> str:
    account = get_mercadopago_account(db, user_id)
    if account is None:
        raise HTTPException(
            status_code=400,
            detail="Mercado Pago não conectado. Acesse GET /mercadopago/connect primeiro.",
        )
    access = ensure_user_mercadopago_access_token(db, account)
    init_point, _ = pay.mercadopago_create_preference_simple(
        access,
        title=title,
        quantity=quantity,
        unit_price=unit_price,
    )
    return init_point
