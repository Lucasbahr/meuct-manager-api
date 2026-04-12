from decimal import Decimal

from app.models.graduation import Graduation
from app.models.modality import Modality
from app.models.student import Student


def test_post_student_modalities_and_list(client, admin_token, user, db):
    m = db.query(Modality).filter(Modality.name == "Jiu Jitsu").first()
    if not m:
        m = Modality(name="Jiu Jitsu")
        db.add(m)
        db.flush()
    g = (
        db.query(Graduation)
        .filter(
            Graduation.gym_id == 1,
            Graduation.modality_id == m.id,
            Graduation.level == 1,
        )
        .first()
    )
    if not g:
        g = Graduation(
            gym_id=1,
            modality_id=m.id,
            name="Branca",
            level=1,
            required_hours=Decimal("0"),
        )
        db.add(g)
        db.commit()
        db.refresh(g)

    st = Student(user_id=user.id, nome="Multi", telefone="11999999999")
    db.add(st)
    db.commit()
    db.refresh(st)

    h = {"Authorization": f"Bearer {admin_token}"}
    r = client.post(
        "/student-modalities",
        headers=h,
        json={
            "student_id": st.id,
            "modality_id": m.id,
            "graduation_id": g.id,
            "hours_trained": "5.5",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert len(data) == 1
    assert data[0]["modality_name"] == "Jiu Jitsu"
    assert Decimal(data[0]["hours_trained"]) == Decimal("5.5")

    lst = client.get(f"/students/{st.id}/modalities", headers=h)
    assert lst.status_code == 200
    assert len(lst.json()["data"]) == 1
