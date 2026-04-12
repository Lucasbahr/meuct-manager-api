from decimal import Decimal

from app.models.student import Student


def _ensure_student(db, user_id: int):
    s = db.query(Student).filter(Student.user_id == user_id).first()
    if s is None:
        s = Student(user_id=user_id, nome="Buyer", telefone="1")
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def test_gym_sales_dashboard_after_paid_order(
    client, admin_token, user_token, user, db, monkeypatch
):
    _ensure_student(db, user.id)
    ha = {"Authorization": f"Bearer {admin_token}"}
    hu = {"Authorization": f"Bearer {user_token}"}

    cat = client.post("/categories", headers=ha, json={"name": "DashCat"}).json()[
        "data"
    ]["id"]
    pid = client.post(
        "/products",
        headers=ha,
        json={
            "name": "ProdDash",
            "price": "100.00",
            "stock": 5,
            "category_id": cat,
            "image_urls": [],
        },
    ).json()["data"]["id"]

    client.post(
        "/payment/config",
        headers=ha,
        json={"provider": "paypal", "client_id": "a", "client_secret": "b"},
    )
    monkeypatch.setattr(
        "app.services.marketplace_payment._paypal_oauth",
        lambda s: "t",
    )
    monkeypatch.setattr(
        "app.services.marketplace_payment.paypal_create_checkout",
        lambda *a, **k: ("https://x", "PO-D"),
    )

    oid = client.post(
        "/orders",
        headers=hu,
        json={"items": [{"product_id": pid, "quantity": 1}]},
    ).json()["data"]["id"]
    client.post(
        f"/orders/{oid}/checkout",
        headers=hu,
        json={
            "provider": "paypal",
            "return_url": "https://a",
            "cancel_url": "https://b",
        },
    )
    client.post(
        "/webhooks/paypal/1",
        json={
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"custom_id": str(oid)},
        },
    )

    from app.models.commission import PlatformCommission

    comm = db.query(PlatformCommission).filter(PlatformCommission.order_id == oid).first()
    assert comm is not None
    assert comm.commission_amount == Decimal("3.00")

    r = client.get("/dashboard/sales?days=30", headers=ha)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["total_orders"] >= 1
    assert data["total_sales"] >= 100.0
    assert data["total_commission"] >= 3.0
    assert len(data["top_products"]) >= 1
    assert data["top_products"][0]["product_id"] == pid


def test_admin_platform_dashboard(client, db):
    from app.services.user_service import create_user

    create_user(
        db,
        "sys-dash@test.com",
        "123456",
        role="ADMIN_SISTEMA",
        gym_id=None,
    )
    login = client.post(
        "/auth/login",
        json={"email": "sys-dash@test.com", "password": "123456"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]

    r = client.get(
        "/admin/dashboard?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert "total_revenue" in body
    assert "total_orders" in body
    assert "total_academies" in body
    assert "top_academies" in body
