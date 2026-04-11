from app.models.student import Student


def _student(db, user_id: int):
    s = db.query(Student).filter(Student.user_id == user_id).first()
    if s is None:
        s = Student(user_id=user_id, nome="S", telefone="1")
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def test_stock_add_remove_and_history(client, admin_token, user, db):
    _student(db, user.id)
    h = {"Authorization": f"Bearer {admin_token}"}

    cat = client.post("/categories", headers=h, json={"name": "StockCat"}).json()["data"][
        "id"
    ]
    pid = client.post(
        "/products",
        headers=h,
        json={
            "name": "Kimono",
            "price": "200.00",
            "stock": 8,
            "category_id": cat,
            "image_urls": [],
        },
    ).json()["data"]["id"]

    g = client.get(f"/stock/{pid}", headers=h)
    assert g.status_code == 200
    assert g.json()["data"]["quantity"] == 8
    assert g.json()["data"]["track_stock"] is True
    assert len(g.json()["data"]["movements"]) >= 1

    a = client.post(
        "/stock/add",
        headers=h,
        json={"product_id": pid, "quantity": 2},
    )
    assert a.status_code == 200
    assert client.get(f"/stock/{pid}", headers=h).json()["data"]["quantity"] == 10

    r = client.post(
        "/stock/remove",
        headers=h,
        json={"product_id": pid, "quantity": 3, "reason": "loss"},
    )
    assert r.status_code == 200
    assert client.get(f"/stock/{pid}", headers=h).json()["data"]["quantity"] == 7

    hist = client.get(f"/stock/movements?product_id={pid}&sort=desc", headers=h)
    assert hist.status_code == 200
    rows = hist.json()["data"]
    assert len(rows) >= 3
    reasons = {x["reason"] for x in rows}
    assert "purchase" in reasons
    assert "manual" in reasons
    assert "loss" in reasons


def test_sale_creates_notification(client, admin_token, user_token, user, db, monkeypatch):
    _student(db, user.id)
    ha = {"Authorization": f"Bearer {admin_token}"}
    hu = {"Authorization": f"Bearer {user_token}"}

    cat = client.post("/categories", headers=ha, json={"name": "N"}).json()["data"]["id"]
    pid = client.post(
        "/products",
        headers=ha,
        json={"name": "P", "price": "1", "stock": 6, "category_id": cat, "image_urls": []},
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
        lambda *a, **k: ("https://x", "PO-2"),
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

    notifs = client.get("/notifications", headers=ha).json()["data"]
    types = {n["type"] for n in notifs}
    assert "sale" in types
    assert "stock_low" in types
