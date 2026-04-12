def test_get_students(client, admin_token):
    response = client.get(
        "/students/", headers={"Authorization": f"Bearer {admin_token}"}
    )

    data = response.json()

    assert "data" in data
    assert isinstance(data["data"], list)


def test_list_athletes_requires_auth(client):
    r = client.get("/students/athletes")
    assert r.status_code in (401, 403)


def test_list_athletes_for_aluno(client, user_token, user, admin_user, db):
    from app.models.student import Student

    db.add(
        Student(
            user_id=user.id,
            nome="Eu Atleta",
            telefone="+5511999999999",
            e_atleta=True,
        )
    )
    db.add(
        Student(
            user_id=admin_user.id,
            nome="Admin Nao Atleta",
            telefone="+5511888888888",
            e_atleta=False,
        )
    )
    db.commit()

    r = client.get(
        "/students/athletes",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    nomes = {x["nome"] for x in body["data"]}
    assert "Eu Atleta" in nomes
    assert "Admin Nao Atleta" not in nomes


def test_get_student_not_found(client, admin_token):
    response = client.get(
        "/students/me/9999", headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 404


def test_create_student_unauthorized(client):
    response = client.post("/students", json={"name": "Aluno", "email": "a@test.com"})

    assert response.status_code == 401


def test_update_my_profile(client, user_token, user, db):
    from app.models.student import Student

    student = Student(
        user_id=user.id,
        nome="Nome Antigo",
        telefone="11999999999",
        endereco="Antigo",
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
    from app.services.user_service import create_user

    aluno = create_user(db, "aluno-upd@test.com", "123456")
    student = Student(
        user_id=aluno.id, nome="Aluno", telefone="11999999999", endereco="Rua A"
    )
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


def test_admin_sets_professor_modalities(client, admin_token, db):
    from app.models.modality import Modality
    from app.models.student import Student
    from app.services.user_service import create_user

    aluno = create_user(db, "prof-mod@test.com", "123456")
    student = Student(
        user_id=aluno.id,
        nome="Professor X",
        telefone="11999999999",
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    m = db.query(Modality).filter(Modality.name == "Muay Thai").first()
    assert m is not None

    r = client.put(
        f"/students/{student.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"professor_modality_ids": [m.id]},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["e_professor"] is True
    assert len(data["professor_modalities"]) == 1
    assert data["professor_modalities"][0]["modality_id"] == m.id
    assert data["professor_modalities"][0]["modality_name"] == "Muay Thai"

    r2 = client.put(
        f"/students/{student.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"e_professor": False},
    )
    assert r2.status_code == 200
    cleared = r2.json()["data"]
    assert cleared["e_professor"] is False
    assert cleared["professor_modalities"] == []


def test_user_cannot_update_other_student(client, user_token, db):
    from app.models.student import Student
    from app.services.user_service import create_user

    outro_u = create_user(db, "outro-upd@test.com", "123456")
    student = Student(user_id=outro_u.id, nome="Outro")
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
    from app.services.user_service import create_user

    aluno = create_user(db, "aluno-inv@test.com", "123456")
    student = Student(user_id=aluno.id, nome="Aluno")
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
    from app.services.user_service import create_user

    aluno = create_user(db, "aluno-nodata@test.com", "123456")
    student = Student(user_id=aluno.id, nome="Aluno")
    db.add(student)
    db.commit()

    response = client.put(
        f"/students/{student.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={},
    )

    assert response.status_code == 400


def test_update_my_profile_atleta(client, user_token, user, db):
    from app.models.student import Student

    student = Student(
        user_id=user.id,
        nome="Nome",
        telefone="+5511999999999",
        endereco="Rua",
    )
    db.add(student)
    db.commit()

    response = client.put(
        "/students/me",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "e_atleta": True,
            "cartel_mma": "5-1-0",
            "cartel_jiu": "12-3",
            "cartel_k1": "2-0-0",
            "nivel_competicao": "amador",
            "link_tapology": "https://www.tapology.com/fightcenter/fighters/123",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["e_atleta"] is True
    assert data["cartel_mma"] == "5-1-0"
    assert data["cartel_jiu"] == "12-3"
    assert data["cartel_k1"] == "2-0-0"
    assert data["nivel_competicao"] == "amador"
    assert "tapology.com" in data["link_tapology"]


def test_update_my_profile_nivel_invalido(client, user_token, user, db):
    from app.models.student import Student

    db.add(Student(user_id=user.id, nome="A", telefone="+5511999999999"))
    db.commit()

    response = client.put(
        "/students/me",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"nivel_competicao": "semi-pro"},
    )

    assert response.status_code == 422


def test_update_my_profile_ultima_luta(client, user_token, user, db):
    from app.models.student import Student

    db.add(
        Student(user_id=user.id, nome="A", telefone="+5511999999999", endereco="X")
    )
    db.commit()

    response = client.put(
        "/students/me",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "ultima_luta_em": "2025-11-08",
            "ultima_luta_modalidade": "MMA",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["ultima_luta_em"] == "2025-11-08"
    assert data["ultima_luta_modalidade"] == "MMA"
    assert data.get("foto_url") is None


# JPEG mínimo válido (1×1 px)
_MIN_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
    b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c"
    b" $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01"
    b"\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4"
    b"\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9"
)


def test_upload_and_get_my_photo(client, user_token, user, db):
    from app.models.student import Student

    db.add(Student(user_id=user.id, nome="A", telefone="+5511999999999"))
    db.commit()

    up = client.post(
        "/students/me/photo",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("x.jpg", _MIN_JPEG, "image/jpeg")},
    )
    assert up.status_code == 200
    body = up.json()
    assert body["data"]["foto_url"] == f"/students/{body['data']['id']}/photo"

    get = client.get(
        "/students/me/photo",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert get.status_code == 200
    assert get.content == _MIN_JPEG
    assert "image" in (get.headers.get("content-type") or "")


def test_get_other_student_photo_forbidden(client, user_token, user, db):
    from app.models.student import Student
    from app.services.user_service import create_user

    db.add(
        Student(
            user_id=user.id,
            nome="Eu",
            telefone="+5511999999999",
            foto_path="s/1/x.jpg",
        )
    )
    outro_u = create_user(db, "outro-photo@test.com", "123456")
    other = Student(
        user_id=outro_u.id,
        nome="Outro",
        telefone="+5511888888888",
        foto_path="s/2/x.jpg",
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    r = client.get(
        f"/students/{other.id}/photo",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 403


def test_admin_upload_athlete_card_and_aluno_can_get(
    client, admin_token, user_token, admin_user, db
):
    from app.models.student import Student

    athlete_stu = Student(
        user_id=admin_user.id,
        nome="Atleta Card",
        telefone="+5511777777777",
        e_atleta=True,
    )
    db.add(athlete_stu)
    db.commit()
    db.refresh(athlete_stu)

    up = client.post(
        f"/students/{athlete_stu.id}/athlete-card/photo",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("c.jpg", _MIN_JPEG, "image/jpeg")},
    )
    assert up.status_code == 200
    data = up.json()["data"]
    assert data["foto_atleta_url"] == f"/students/{athlete_stu.id}/athlete-card/photo"

    get = client.get(
        f"/students/{athlete_stu.id}/athlete-card/photo",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert get.status_code == 200
    assert get.content == _MIN_JPEG


def test_upload_athlete_card_requires_admin(client, user_token, user, db):
    from app.models.student import Student

    st = Student(
        user_id=user.id,
        nome="A",
        telefone="+5511999999999",
        e_atleta=True,
    )
    db.add(st)
    db.commit()
    db.refresh(st)

    r = client.post(
        f"/students/{st.id}/athlete-card/photo",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("c.jpg", _MIN_JPEG, "image/jpeg")},
    )
    assert r.status_code == 403


def test_get_athlete_card_non_atleta_forbidden(
    client, admin_token, user_token, admin_user, db
):
    from app.models.student import Student

    athlete_stu = Student(
        user_id=admin_user.id,
        nome="X",
        telefone="+5511666666666",
        e_atleta=True,
    )
    db.add(athlete_stu)
    db.commit()
    db.refresh(athlete_stu)

    client.post(
        f"/students/{athlete_stu.id}/athlete-card/photo",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("c.jpg", _MIN_JPEG, "image/jpeg")},
    )

    athlete_stu.e_atleta = False
    db.commit()

    r = client.get(
        f"/students/{athlete_stu.id}/athlete-card/photo",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 403
