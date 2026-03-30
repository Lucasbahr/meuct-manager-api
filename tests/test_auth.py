from app.services.user_service import create_user
from app.models.user import User
from app.core.security import create_access_token, create_reset_token
from unittest.mock import patch

# =========================
# REGISTER
# =========================


def test_register_success(client):
    response = client.post(
        "/auth/register", json={"email": "new@teste.com", "password": "123456"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["data"]["email"] == "new@teste.com"


def test_register_duplicate_email(client):
    payload = {"email": "dup@teste.com", "password": "123456"}

    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)

    assert response.status_code in [400, 409]


def test_register_duplicate_email_case_insensitive(client):
    client.post(
        "/auth/register", json={"email": "Case@Teste.com", "password": "123456"}
    )
    response = client.post(
        "/auth/register", json={"email": "case@teste.com", "password": "123456"}
    )
    assert response.status_code in [400, 409]


# =========================
# LOGIN
# =========================


def test_login_success(client, db):
    create_user(db, "login@teste.com", "123456")

    response = client.post(
        "/auth/login", json={"email": "login@teste.com", "password": "123456"}
    )

    assert response.status_code == 200
    assert "access_token" in response.json()["data"]
    assert "refresh_token" in response.json()["data"]


def test_login_wrong_password(client, db):
    create_user(db, "login2@teste.com", "123456")

    response = client.post(
        "/auth/login", json={"email": "login2@teste.com", "password": "errada"}
    )

    assert response.status_code == 401


def test_login_user_not_found(client):
    response = client.post(
        "/auth/login", json={"email": "naoexiste@teste.com", "password": "123456"}
    )

    assert response.status_code == 401


def test_login_case_insensitive_email(client, db):
    create_user(db, "caps@teste.com", "123456")
    response = client.post(
        "/auth/login", json={"email": "CAPS@TESTE.COM", "password": "123456"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


# =========================
# VERIFY EMAIL
# =========================


def test_verify_email_success(client, db):
    user = User(email="verify@teste.com", password="123", role="ALUNO")
    db.add(user)
    db.commit()
    db.refresh(user)

    with patch("app.routes.auth_routes.decode_token") as mock_decode:
        mock_decode.return_value = {"user_id": user.id, "type": "email_verification"}

        response = client.get("/auth/verify-email?token=fake")

        assert response.status_code == 200


def test_verify_email_invalid_token(client):
    response = client.get("/auth/verify-email?token=token_invalido")

    assert response.status_code == 400


def test_verify_email_wrong_type(client):
    token = create_access_token({"user_id": 1, "type": "access"})

    response = client.get(f"/auth/verify-email?token={token}")

    assert response.status_code == 400


# =========================
# RESEND VERIFICATION
# =========================


def test_resend_verification(client):
    with patch("app.routes.auth_routes.resend_verification_email") as mock_email:
        response = client.post(
            "/auth/resend-verification", params={"email": "teste@teste.com"}
        )

        assert response.status_code == 200
        mock_email.assert_called_once()


def test_resend_verification_without_email(client):
    response = client.post("/auth/resend-verification")

    assert response.status_code == 422


# =========================
# FORGOT PASSWORD
# =========================


def test_forgot_password_existing_user(client, db):
    user = User(email="forgot@teste.com", password="123", role="ALUNO")
    db.add(user)
    db.commit()

    response = client.post("/auth/forgot-password?email=forgot@teste.com")

    assert response.status_code == 200


def test_forgot_password_case_insensitive(client, db):
    user = User(email="mixed@teste.com", password="123", role="ALUNO")
    db.add(user)
    db.commit()
    response = client.post("/auth/forgot-password?email=MIXED@TESTE.COM")
    assert response.status_code == 200


def test_forgot_password_non_existing(client):
    response = client.post("/auth/forgot-password?email=nao@teste.com")

    assert response.status_code == 200


# =========================
# RESET PASSWORD
# =========================


def test_reset_password_success(client, db):
    user = User(email="reset@teste.com", password="123", role="ALUNO")
    db.add(user)
    db.commit()

    token = create_reset_token(user.email)

    response = client.post(f"/auth/reset-password?token={token}&new_password=654321")

    assert response.status_code == 200


def test_reset_password_invalid_token(client):
    response = client.post("/auth/reset-password?token=invalido&new_password=123")

    assert response.status_code == 400


def test_reset_password_user_not_found(client):
    token = create_reset_token("naoexiste@teste.com")

    response = client.post(f"/auth/reset-password?token={token}&new_password=123")

    assert response.status_code == 404


# =========================
# CHANGE PASSWORD
# =========================


def test_change_password_success(client, db):
    create_user(db, "change@teste.com", "123456")

    login = client.post(
        "/auth/login", json={"email": "change@teste.com", "password": "123456"}
    )

    token = login.json()["data"]["access_token"]

    response = client.put(
        "/auth/change-password",
        params={"current_password": "123456", "new_password": "654321"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_change_password_wrong_current(client, db):
    create_user(db, "change2@teste.com", "123456")

    login = client.post(
        "/auth/login", json={"email": "change2@teste.com", "password": "123456"}
    )

    token = login.json()["data"]["access_token"]

    response = client.put(
        "/auth/change-password",
        params={"current_password": "errada", "new_password": "654321"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


def test_change_password_without_token(client):
    response = client.put(
        "/auth/change-password",
        params={"current_password": "123", "new_password": "456"},
    )

    assert response.status_code == 401


def test_refresh_session(client, db):
    create_user(db, "refresh@teste.com", "123456")
    login = client.post(
        "/auth/login", json={"email": "refresh@teste.com", "password": "123456"}
    )
    refresh_token = login.json()["data"]["refresh_token"]

    response = client.post(f"/auth/refresh?refresh_token={refresh_token}")
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


def test_logout_revokes_refresh_token(client, db):
    create_user(db, "logout@teste.com", "123456")
    login = client.post(
        "/auth/login", json={"email": "logout@teste.com", "password": "123456"}
    )
    refresh_token = login.json()["data"]["refresh_token"]

    out = client.post(f"/auth/logout?refresh_token={refresh_token}")
    assert out.status_code == 200

    retry = client.post(f"/auth/refresh?refresh_token={refresh_token}")
    assert retry.status_code == 401
