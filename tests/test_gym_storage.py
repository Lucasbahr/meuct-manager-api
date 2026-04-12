def test_create_gym_provisions_tenant_markers(client, db, monkeypatch, tmp_path):
    from app.services.user_service import create_user

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.setenv("GCS_PROVISION_TENANT_ON_CREATE", "true")

    create_user(
        db,
        "sys-gym-create@test.com",
        "123456",
        role="ADMIN_SISTEMA",
        gym_id=None,
    )
    login = client.post(
        "/auth/login",
        json={"email": "sys-gym-create@test.com", "password": "123456"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]

    r = client.post(
        "/gyms",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Academia Nova"},
    )
    assert r.status_code == 200, r.text
    gid = r.json()["data"]["id"]

    base = tmp_path / "up" / "tenants" / str(gid)
    assert (base / "students" / ".keep").is_file()
    assert (base / "feed_items" / ".keep").is_file()
    assert (base / "marketplace" / ".keep").is_file()
