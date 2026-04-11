def test_create_gym_provisions_tenant_markers(client, monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.setenv("GCS_PROVISION_TENANT_ON_CREATE", "true")

    r = client.post("/gyms", json={"name": "Academia Nova"})
    assert r.status_code == 200, r.text
    gid = r.json()["data"]["id"]

    base = tmp_path / "up" / "tenants" / str(gid)
    assert (base / "students" / ".keep").is_file()
    assert (base / "feed_items" / ".keep").is_file()
    assert (base / "marketplace" / ".keep").is_file()
