from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.student import Student


def _ensure_student(db: Session, user_id: int):
    s = db.query(Student).filter(Student.user_id == user_id).first()
    if s is None:
        s = Student(user_id=user_id, nome="Comprador", telefone="11999999999")
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def test_marketplace_admin_and_catalog(client, admin_token, user_token, user, db):
    _ensure_student(db, user.id)

    h_admin = {"Authorization": f"Bearer {admin_token}"}
    h_user = {"Authorization": f"Bearer {user_token}"}

    c = client.post("/categories", headers=h_admin, json={"name": "Equipamentos"})
    assert c.status_code == 200, c.text
    cat_id = c.json()["data"]["id"]

    sc = client.post(
        "/subcategories",
        headers=h_admin,
        json={"category_id": cat_id, "name": "Luvas"},
    )
    assert sc.status_code == 200, sc.text
    sub_id = sc.json()["data"]["id"]

    p = client.post(
        "/products",
        headers=h_admin,
        json={
            "name": "Luva 12oz",
            "description": "Couro",
            "price": "99.90",
            "stock": 5,
            "is_active": True,
            "category_id": cat_id,
            "subcategory_id": sub_id,
            "image_urls": ["https://example.com/a.jpg", "https://example.com/b.jpg"],
        },
    )
    assert p.status_code == 200, p.text
    pdata = p.json()["data"]
    pid = pdata["id"]
    assert len(pdata["images"]) == 2

    lst = client.get("/products", headers=h_user)
    assert lst.status_code == 200
    assert len(lst.json()["data"]) == 1

    f = client.get(f"/products/{pid}", headers=h_user)
    assert f.status_code == 200
    assert f.json()["data"]["price"] == "99.90"

    flt = client.get(
        f"/products?category_id={cat_id}&subcategory_id={sub_id}",
        headers=h_user,
    )
    assert flt.status_code == 200
    assert len(flt.json()["data"]) == 1


def test_order_create_and_checkout_mock(client, admin_token, user_token, user, db, monkeypatch):
    _ensure_student(db, user.id)
    h_admin = {"Authorization": f"Bearer {admin_token}"}
    h_user = {"Authorization": f"Bearer {user_token}"}

    cat_id = client.post("/categories", headers=h_admin, json={"name": "C2"}).json()[
        "data"
    ]["id"]
    pid = client.post(
        "/products",
        headers=h_admin,
        json={
            "name": "Item",
            "price": "10.00",
            "stock": 3,
            "category_id": cat_id,
            "image_urls": [],
        },
    ).json()["data"]["id"]

    client.post(
        "/payment/config",
        headers=h_admin,
        json={
            "provider": "paypal",
            "client_id": "x",
            "client_secret": "y",
        },
    )

    def fake_paypal(settings, order, return_url, cancel_url):
        return "https://paypal.test/approve", "PAYPAL-ORDER-X"

    monkeypatch.setattr(
        "app.services.marketplace_payment.paypal_create_checkout",
        fake_paypal,
    )

    def fake_oauth(settings):
        return "fake-token"

    monkeypatch.setattr(
        "app.services.marketplace_payment._paypal_oauth",
        fake_oauth,
    )

    o = client.post(
        "/orders",
        headers=h_user,
        json={"items": [{"product_id": pid, "quantity": 2}]},
    )
    assert o.status_code == 200, o.text
    oid = o.json()["data"]["id"]
    assert Decimal(o.json()["data"]["total_amount"]) == Decimal("20.00")

    ch = client.post(
        f"/orders/{oid}/checkout",
        headers=h_user,
        json={
            "provider": "paypal",
            "return_url": "https://app.test/ok",
            "cancel_url": "https://app.test/cancel",
        },
    )
    assert ch.status_code == 200, ch.text
    body = ch.json()["data"]
    assert body["redirect_url"] == "https://paypal.test/approve"
    assert body["external_checkout_id"] == "PAYPAL-ORDER-X"

    # estoque só baixa após webhook / pago
    detail = client.get(f"/products/{pid}", headers=h_user).json()["data"]
    assert detail["stock"] == 3


def test_professor_cannot_create_product(client, db):
    from app.services.user_service import create_user

    prof = create_user(
        db, "prof-mp@test.com", "123456", role="PROFESSOR", gym_id=1
    )
    r = client.post(
        "/auth/login", json={"email": "prof-mp@test.com", "password": "123456"}
    )
    token = r.json()["data"]["access_token"]
    resp = client.post(
        "/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "X", "price": "1", "stock": 1, "image_urls": []},
    )
    assert resp.status_code == 403


def test_paypal_webhook_marks_paid(client, admin_token, user_token, user, db, monkeypatch):
    _ensure_student(db, user.id)
    h_admin = {"Authorization": f"Bearer {admin_token}"}
    h_user = {"Authorization": f"Bearer {user_token}"}

    cat_id = client.post("/categories", headers=h_admin, json={"name": "W"}).json()[
        "data"
    ]["id"]
    pid = client.post(
        "/products",
        headers=h_admin,
        json={"name": "Z", "price": "5.00", "stock": 10, "category_id": cat_id},
    ).json()["data"]["id"]

    client.post(
        "/payment/config",
        headers=h_admin,
        json={"provider": "paypal", "client_id": "a", "client_secret": "b"},
    )

    def fake_oauth(settings):
        return "t"

    monkeypatch.setattr(
        "app.services.marketplace_payment._paypal_oauth",
        fake_oauth,
    )

    monkeypatch.setattr(
        "app.services.marketplace_payment.paypal_create_checkout",
        lambda *a, **k: ("https://x", "PO-1"),
    )

    oid = client.post(
        "/orders",
        headers=h_user,
        json={"items": [{"product_id": pid, "quantity": 1}]},
    ).json()["data"]["id"]
    client.post(
        f"/orders/{oid}/checkout",
        headers=h_user,
        json={
            "provider": "paypal",
            "return_url": "https://a",
            "cancel_url": "https://b",
        },
    )

    wh = client.post(
        "/webhooks/paypal/1",
        json={
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"custom_id": str(oid)},
        },
    )
    assert wh.status_code == 200, wh.text
    assert wh.json().get("paid") is True

    stock = client.get(f"/products/{pid}", headers=h_user).json()["data"]["stock"]
    assert stock == 9


def test_mercadopago_oauth_start_requires_server_config(client, admin_token, monkeypatch):
    monkeypatch.delenv("MERCADOPAGO_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("MERCADOPAGO_OAUTH_REDIRECT_URI", raising=False)
    r = client.post(
        "/payment/mercado-pago/oauth/start",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={},
    )
    assert r.status_code == 503


def test_mercadopago_oauth_next_url_requires_prefix(client, admin_token, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_OAUTH_CLIENT_ID", "app123")
    monkeypatch.setenv("MERCADOPAGO_OAUTH_REDIRECT_URI", "https://api.test/callback")
    r = client.post(
        "/payment/mercado-pago/oauth/start",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"next_url": "https://evil.example/steal"},
    )
    assert r.status_code == 400


def test_mercadopago_oauth_start_and_callback(client, admin_token, db, monkeypatch):
    from urllib.parse import parse_qs, urlparse

    from app.models.marketplace import GymPaymentSettings

    monkeypatch.setenv("MERCADOPAGO_OAUTH_CLIENT_ID", "app123")
    monkeypatch.setenv("MERCADOPAGO_OAUTH_CLIENT_SECRET", "secret456")
    monkeypatch.setenv("MERCADOPAGO_OAUTH_REDIRECT_URI", "https://api.test/callback")

    start = client.post(
        "/payment/mercado-pago/oauth/start",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={},
    )
    assert start.status_code == 200, start.text
    auth_url = start.json()["data"]["authorization_url"]
    parsed = urlparse(auth_url)
    assert "mercadopago.com" in parsed.netloc
    qs = parse_qs(parsed.query)
    state = qs["state"][0]
    assert qs["client_id"] == ["app123"]

    def fake_exchange(*_a, **_k):
        return {
            "access_token": "AT-OAUTH",
            "refresh_token": "RT-OAUTH",
            "user_id": 777,
        }

    monkeypatch.setattr(
        "app.services.marketplace_payment.mercadopago_oauth_exchange_code",
        fake_exchange,
    )

    cb = client.get(
        "/payment/mercado-pago/oauth/callback",
        params={"code": "auth-code-test", "state": state},
        follow_redirects=False,
    )
    assert cb.status_code == 200
    assert "conectado" in cb.text.lower()

    row = (
        db.query(GymPaymentSettings)
        .filter(
            GymPaymentSettings.gym_id == 1,
            GymPaymentSettings.provider == "mercado_pago",
        )
        .first()
    )
    assert row is not None
    assert row.access_token is not None


def test_mercadopago_oauth_callback_redirects_when_next_url(client, admin_token, monkeypatch):
    from urllib.parse import parse_qs, urlparse

    monkeypatch.setenv("MERCADOPAGO_OAUTH_CLIENT_ID", "app")
    monkeypatch.setenv("MERCADOPAGO_OAUTH_CLIENT_SECRET", "sec")
    monkeypatch.setenv("MERCADOPAGO_OAUTH_REDIRECT_URI", "https://api.test/cb")
    monkeypatch.setenv(
        "MERCADOPAGO_OAUTH_SUCCESS_URL_PREFIX", "https://app.frontend.test"
    )

    start = client.post(
        "/payment/mercado-pago/oauth/start",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"next_url": "https://app.frontend.test/gym/pagamentos"},
    )
    assert start.status_code == 200, start.text
    qs = parse_qs(urlparse(start.json()["data"]["authorization_url"]).query)
    state = qs["state"][0]

    monkeypatch.setattr(
        "app.services.marketplace_payment.mercadopago_oauth_exchange_code",
        lambda *a, **k: {"access_token": "t1", "refresh_token": "r1", "user_id": 1},
    )

    cb = client.get(
        "/payment/mercado-pago/oauth/callback",
        params={"code": "c1", "state": state},
        follow_redirects=False,
    )
    assert cb.status_code == 302
    assert cb.headers["location"] == (
        "https://app.frontend.test/gym/pagamentos?mp_oauth=ok"
    )
