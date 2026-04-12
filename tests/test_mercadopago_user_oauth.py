"""OAuth Mercado Pago por usuário (MP_*) e POST /payments/create."""

from datetime import datetime, timezone
from unittest.mock import patch

from app.core.security import create_mercadopago_user_oauth_state
from app.models.mercadopago_account import MercadoPagoAccount


def test_mercadopago_user_connect_requires_env(client, admin_token, monkeypatch):
    monkeypatch.delenv("MP_CLIENT_ID", raising=False)
    monkeypatch.delenv("MP_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("MP_REDIRECT_URI", raising=False)
    r = client.get(
        "/mercadopago/connect",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 503


def test_mercadopago_user_connect_returns_br_auth_url(
    client, admin_token, monkeypatch
):
    monkeypatch.setenv("MP_CLIENT_ID", "app_client_id")
    monkeypatch.setenv("MP_CLIENT_SECRET", "secret")
    monkeypatch.setenv("MP_REDIRECT_URI", "https://api.example.com/mercadopago/callback")
    r = client.get(
        "/mercadopago/connect",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    url = r.json()["data"]["url"]
    assert "auth.mercadopago.com.br" in url
    assert "client_id=app_client_id" in url


def test_mercadopago_user_connect_forbidden_for_student(
    client, user_token, monkeypatch
):
    monkeypatch.setenv("MP_CLIENT_ID", "x")
    monkeypatch.setenv("MP_CLIENT_SECRET", "y")
    monkeypatch.setenv("MP_REDIRECT_URI", "https://x/cb")
    r = client.get(
        "/mercadopago/connect",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 403


def test_mercadopago_user_oauth_callback_persists_tokens(
    client, admin_user, db, monkeypatch
):
    monkeypatch.setenv("MP_CLIENT_ID", "cid")
    monkeypatch.setenv("MP_CLIENT_SECRET", "csec")
    monkeypatch.setenv("MP_REDIRECT_URI", "https://cb")
    state = create_mercadopago_user_oauth_state(admin_user.id)

    def fake_exchange(*_a, **_k):
        return {
            "access_token": "acc_tok",
            "refresh_token": "ref_tok",
            "expires_in": 10800,
        }

    with patch(
        "app.services.marketplace_payment.mercadopago_oauth_exchange_code",
        fake_exchange,
    ):
        r = client.get(
            "/mercadopago/callback",
            params={"code": "abc", "state": state},
        )
    assert r.status_code == 200
    row = (
        db.query(MercadoPagoAccount)
        .filter(MercadoPagoAccount.user_id == admin_user.id)
        .first()
    )
    assert row is not None
    assert row.access_token == "acc_tok"
    assert row.refresh_token == "ref_tok"
    assert row.expires_in == 10800


def test_payments_create_without_mp_account(client, admin_token):
    r = client.post(
        "/payments/create",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"unit_price": 10.0},
    )
    assert r.status_code == 400
    assert "não conectado" in r.json()["message"].lower()


def test_payments_create_returns_init_point(client, admin_token, admin_user, db):
    now = datetime.now(timezone.utc)
    db.add(
        MercadoPagoAccount(
            user_id=admin_user.id,
            access_token="plain_token",
            refresh_token="r",
            expires_in=999_999,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()

    def fake_pref(token, **kwargs):
        assert token == "plain_token"
        return "https://checkout.test/init", "pref_1"

    with patch(
        "app.services.mercadopago_account_service.pay.mercadopago_create_preference_simple",
        fake_pref,
    ):
        r = client.post(
            "/payments/create",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"title": "Plano", "quantity": 1, "unit_price": 100.0},
        )
    assert r.status_code == 200
    assert r.json()["data"]["init_point"] == "https://checkout.test/init"
