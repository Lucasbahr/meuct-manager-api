"""SaaS multi-tenant: config agregada, slug, isolamento básico."""


def test_tenant_config_by_slug_public(client):
    r = client.get("/tenant/config?slug=test-gym")
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["tenant"]["slug"] == "test-gym"
    assert "config" in body
    assert "modalidades" in body
    assert "graduacoes" in body
    assert "payment_configs" in body
    assert body["config"]["permite_checkin"] is True


def test_tenant_public_by_slug(client):
    r = client.get("/tenants/test-gym")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["nome"] == "Test Gym"


def test_post_tenants_requires_system_admin(client, admin_token):
    r = client.post(
        "/tenants",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"nome": "Nova Academia"},
    )
    assert r.status_code == 403


def test_post_tenants_system_admin(client, db):
    from app.services.user_service import create_user

    create_user(
        db,
        "sys-tenant@test.com",
        "123456",
        role="ADMIN_SISTEMA",
        gym_id=None,
    )
    login = client.post(
        "/auth/login",
        json={"email": "sys-tenant@test.com", "password": "123456"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]

    r = client.post(
        "/tenants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "nome": "Academia SaaS X",
            "slug": "saas-x",
            "cor_primaria": "#FF0000",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["slug"] == "saas-x"
    assert data["cor_primaria"] == "#FF0000"


def test_register_with_tenant_slug(client, db):
    from app.models.tenant_config import TenantConfig
    from app.models.gym import Gym
    from app.models.user import User

    g = Gym(name="Invite Gym", slug="invite-gym")
    db.add(g)
    db.flush()
    db.add(TenantConfig(gym_id=g.id))
    db.commit()

    r = client.post(
        "/auth/register",
        json={
            "email": "invited@test.com",
            "password": "123456",
            "tenant_slug": "invite-gym",
        },
    )
    assert r.status_code == 200, r.text
    u = db.query(User).filter(User.email == "invited@test.com").first()
    assert u is not None
    assert u.gym_id == g.id
