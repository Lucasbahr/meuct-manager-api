from fastapi import status


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_admin_set_user_role_success(client, db, admin_token):
    from app.models.user import User

    target = User(
        gym_id=1,
        email="role@test.com",
        password="x",
        role="ALUNO",
        is_verified=True,
    )
    db.add(target)
    db.commit()

    response = client.put(
        "/admin/users/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "ROLE@Test.com", "role": "admin"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["role"] == "ADMIN_ACADEMIA"


def test_admin_set_user_role_invalid_and_notfound(client, admin_token):
    invalid = client.put(
        "/admin/users/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "x@test.com", "role": "manager"},
    )
    assert invalid.status_code == status.HTTP_400_BAD_REQUEST

    missing = client.put(
        "/admin/users/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "naoexiste@test.com", "role": "ALUNO"},
    )
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_admin_set_user_role_cannot_demote_self(client, admin_user, admin_token):
    response = client.put(
        "/admin/users/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": admin_user.email, "role": "ALUNO"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_checkin_summary_and_history_flow(client, db, user, user_token):
    from app.models.student import Student
    from app.services import student_modality_service as sm_svc

    from tests.checkin_schedule_helpers import ensure_slot_for_checkin_tests

    student = Student(user_id=user.id, nome="Aluno", telefone="+5511999999999")
    db.add(student)
    db.commit()
    db.refresh(student)
    sm_svc.ensure_default_enrollment(db, 1, student.id)
    db.commit()

    sid = ensure_slot_for_checkin_tests(db)

    do_checkin = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"schedule_slot_id": sid},
    )
    assert do_checkin.status_code == status.HTTP_200_OK

    duplicate = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"schedule_slot_id": sid},
    )
    assert duplicate.status_code == status.HTTP_400_BAD_REQUEST

    summary = client.get(
        "/checkin/me/summary",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert summary.status_code == status.HTTP_200_OK
    assert summary.json()["data"]["total_geral"] >= 1

    history = client.get(
        "/checkin/me/history",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert history.status_code == status.HTTP_200_OK
    assert len(history.json()["data"]) >= 1


def test_feed_get_item_and_comment_requires_item(client, admin_token, user_token):
    create = client.post(
        "/feed/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tipo": "evento", "titulo": "Cobertura"},
    )
    assert create.status_code == status.HTTP_200_OK
    item_id = create.json()["data"]["id"]

    get_item = client.get(
        f"/feed/{item_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert get_item.status_code == status.HTTP_200_OK
    assert get_item.json()["data"]["id"] == item_id

    missing = client.post(
        "/feed/999999/comments",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"conteudo": "x"},
    )
    assert missing.status_code == status.HTTP_404_NOT_FOUND

