def test_create_checkin(client, admin_token):
    response = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"student_id": 1},
    )

    assert response.status_code in [200, 201, 404]


def test_get_checkins(client, admin_token):
    response = client.get(
        "/checkin/ranking", headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200

    data = response.json()

    assert "data" in data
    assert isinstance(data["data"], list)


def test_checkin_invalid_student(client, admin_token):
    response = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"student_id": 9999},
    )

    assert response.status_code == 404


def test_checkin_unauthorized(client):
    response = client.post("/checkin/", json={"student_id": 1})
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

    response = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"student_id": other.id},
    )
    assert response.status_code == 403


def test_admin_checkin_for_student(client, admin_token, user, db):
    from app.models.student import Student

    student = Student(user_id=user.id, nome="Aluno", telefone="+5511999999999")
    db.add(student)
    db.commit()
    db.refresh(student)

    response = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"student_id": student.id},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
