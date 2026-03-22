def test_get_students(client, admin_token):
    response = client.get(
        "/students/", headers={"Authorization": f"Bearer {admin_token}"}
    )

    data = response.json()

    assert "data" in data
    assert isinstance(data["data"], list)


def test_get_student_not_found(client, admin_token):
    response = client.get(
        "/students/me/9999", headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 404


def test_create_student_unauthorized(client):
    response = client.post("/students", json={"name": "Aluno", "email": "a@test.com"})

    assert response.status_code == 401


def test_update_my_profile(client, user_token, db):
    from app.models.student import Student

    student = Student(
        user_id=1, nome="Nome Antigo", telefone="11999999999", endereco="Antigo"
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    response = client.put(
        "/students/me",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "nome": "Novo Nome",
            "telefone": "11999999999",
            "endereco": "Novo Endereco",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["nome"] == "Novo Nome"


def test_admin_update_student(client, admin_token, db):
    from app.models.student import Student

    student = Student(user_id=2, nome="Aluno", telefone="11999999999", endereco="Rua A")
    db.add(student)
    db.commit()
    db.refresh(student)

    response = client.put(
        f"/students/{student.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"nome": "Atualizado pelo admin", "telefone": "11999999999"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["nome"] == "Atualizado pelo admin"


def test_user_cannot_update_other_student(client, user_token, db):
    from app.models.student import Student

    student = Student(user_id=2, nome="Outro")
    db.add(student)
    db.commit()
    db.refresh(student)

    response = client.put(
        f"/students/{student.id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"nome": "hack"},
    )

    assert response.status_code == 403


def test_admin_update_invalid_field(client, admin_token, db):
    from app.models.student import Student

    student = Student(user_id=2, nome="Aluno")
    db.add(student)
    db.commit()

    response = client.put(
        f"/students/{student.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"campo_invalido": "teste"},
    )

    assert response.status_code == 422


def test_admin_update_no_data(client, admin_token, db):
    from app.models.student import Student

    student = Student(user_id=2, nome="Aluno")
    db.add(student)
    db.commit()

    response = client.put(
        f"/students/{student.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={},
    )

    assert response.status_code == 400
