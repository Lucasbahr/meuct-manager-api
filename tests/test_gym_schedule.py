"""Aulas e grade horária por academia."""


def test_gym_schedule_admin_crud_and_public_read(client, admin_token, db):
    from app.models.modality import Modality

    m = db.query(Modality).first()
    assert m is not None
    h = {"Authorization": f"Bearer {admin_token}"}

    c = client.post(
        "/gym-classes",
        headers=h,
        json={
            "name": "Muay Thai Avançado",
            "description": "Sparring leve",
            "modality_id": m.id,
            "instructor_name": "Prof. Teste",
            "duration_minutes": 90,
            "sort_order": 1,
        },
    )
    assert c.status_code == 200, c.text
    cid = c.json()["data"]["id"]

    s = client.post(
        "/gym-schedule/slots",
        headers=h,
        json={
            "gym_class_id": cid,
            "weekday": 2,
            "start_time": "19:30:00",
            "end_time": "21:00:00",
            "room": "Sala A",
        },
    )
    assert s.status_code == 200, s.text
    slot = s.json()["data"]
    assert slot["weekday"] == 2
    assert slot["start_time"] == "19:30"
    assert slot["class_info"]["name"] == "Muay Thai Avançado"

    pub = client.get("/gym-schedule?slug=test-gym&active_only=true")
    assert pub.status_code == 200, pub.text
    assert any(x["id"] == slot["id"] for x in pub.json()["data"])

    grp = client.get("/gym-schedule?slug=test-gym&grouped=true")
    assert grp.status_code == 200
    days = grp.json()["data"]
    assert isinstance(days, list)
    assert any(d["weekday"] == 2 for d in days)

    classes_pub = client.get("/gym-classes?slug=test-gym")
    assert classes_pub.status_code == 200
    assert any(x["id"] == cid for x in classes_pub.json()["data"])

    up = client.patch(
        f"/gym-classes/{cid}",
        headers=h,
        json={"name": "Muay Thai Avançado II"},
    )
    assert up.status_code == 200, up.text

    sid = slot["id"]
    up_slot = client.patch(
        f"/gym-schedule/slots/{sid}",
        headers=h,
        json={"room": "Sala B"},
    )
    assert up_slot.status_code == 200
    assert up_slot.json()["data"]["room"] == "Sala B"

    dl = client.delete(f"/gym-schedule/slots/{sid}", headers=h)
    assert dl.status_code == 200

    dl_c = client.delete(f"/gym-classes/{cid}", headers=h)
    assert dl_c.status_code == 200


def test_gym_schedule_professor_cannot_create_class(client, db):
    from app.services.user_service import create_user

    create_user(
        db,
        "prof-gh@test.com",
        "123456",
        role="PROFESSOR",
        gym_id=1,
    )
    login = client.post(
        "/auth/login",
        json={"email": "prof-gh@test.com", "password": "123456"},
    )
    token = login.json()["data"]["access_token"]
    r = client.post(
        "/gym-classes",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "X"},
    )
    assert r.status_code == 403
