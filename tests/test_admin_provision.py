def test_admin_provision_user_academy_admin(client, admin_token):
    h = {"Authorization": f"Bearer {admin_token}"}
    r = client.post(
        "/admin/users/provision",
        headers=h,
        json={
            "email": "novoprof@test.com",
            "password": "senha12",
            "role": "PROFESSOR",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["email"] == "novoprof@test.com"
    assert data["role"] == "PROFESSOR"
    assert data["gym_id"] == 1

    login = client.post(
        "/auth/login",
        json={"email": "novoprof@test.com", "password": "senha12"},
    )
    assert login.status_code == 200, login.text


def test_admin_provision_system_admin_other_gym(client, db):
    from app.services.user_service import create_user
    from app.models.gym import Gym

    g = Gym(name="Gym B", slug="gym-b-test-prov")
    db.add(g)
    db.commit()
    db.refresh(g)

    create_user(
        db,
        "sysprov@test.com",
        "123456",
        role="ADMIN_SISTEMA",
        gym_id=None,
    )
    login = client.post(
        "/auth/login",
        json={"email": "sysprov@test.com", "password": "123456"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]
    h = {
        "Authorization": f"Bearer {token}",
        "X-Gym-Id": str(g.id),
    }
    r = client.post(
        "/admin/users/provision",
        headers=h,
        json={
            "email": "adminb@test.com",
            "password": "senha12",
            "role": "ADMIN_ACADEMIA",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["gym_id"] == g.id
