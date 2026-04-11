from tests.checkin_schedule_helpers import ensure_slot_for_checkin_tests


def test_create_checkin(client, admin_token, user, db):
    from app.models.student import Student
    from app.services import student_modality_service as sm_svc

    student = Student(user_id=user.id, nome="Aluno", telefone="+5511999999999")
    db.add(student)
    db.commit()
    db.refresh(student)
    sm_svc.ensure_default_enrollment(db, 1, student.id)
    db.commit()

    sid = ensure_slot_for_checkin_tests(db)

    response = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"student_id": student.id, "schedule_slot_id": sid},
    )

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    data = response.json()["data"]
    assert data["schedule_slot_id"] == sid
    assert data["hours_credited"] >= 1.0


def test_get_checkins(client, admin_token):
    response = client.get(
        "/checkin/ranking", headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200

    data = response.json()

    assert "data" in data
    assert isinstance(data["data"], list)


def test_checkin_invalid_student(client, admin_token, db):
    sid = ensure_slot_for_checkin_tests(db)
    response = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"student_id": 9999, "schedule_slot_id": sid},
    )

    assert response.status_code == 404


def test_checkin_unauthorized(client, db):
    sid = ensure_slot_for_checkin_tests(db)
    response = client.post("/checkin/", json={"schedule_slot_id": sid})
    assert response.status_code == 401


def test_checkin_non_admin_cannot_set_student_id(client, user_token, db):
    from app.models.student import Student
    from app.services.user_service import create_user

    other_user = create_user(
        db=db, email="othercheckin@test.com", password="123456", is_verified=True
    )
    other = Student(
        user_id=other_user.id, nome="Outro", telefone="+5511999999999"
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    sid = ensure_slot_for_checkin_tests(db)

    response = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"student_id": other.id, "schedule_slot_id": sid},
    )
    assert response.status_code == 403


def test_admin_checkin_for_student(client, admin_token, user, db):
    from app.models.student import Student
    from app.services import student_modality_service as sm_svc

    student = Student(user_id=user.id, nome="Aluno", telefone="+5511999999999")
    db.add(student)
    db.commit()
    db.refresh(student)
    sm_svc.ensure_default_enrollment(db, 1, student.id)
    db.commit()

    sid = ensure_slot_for_checkin_tests(db)

    response = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"student_id": student.id, "schedule_slot_id": sid},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
