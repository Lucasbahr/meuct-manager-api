from decimal import Decimal

from app.core.gamification_constants import (
    BADGE_FIRST_GRADUATION,
    BADGE_STREAK_7,
    BADGE_WARRIOR_100,
)
from app.models.gamification import Badge
from app.models.graduation import Graduation
from app.models.modality import Modality
from app.models.student import Student
from app.models.student_modality import StudentModality


def _seed_badges(db):
    for name, desc in (
        (BADGE_FIRST_GRADUATION, "Primeira graduação"),
        (BADGE_STREAK_7, "7 dias seguidos"),
        (BADGE_WARRIOR_100, "100 treinos"),
    ):
        if db.query(Badge).filter(Badge.name == name).first() is None:
            db.add(Badge(name=name, description=desc, icon=None))
    db.commit()


def _training_setup(db, user):
    _seed_badges(db)
    m = Modality(name="Muay Thai")
    db.add(m)
    db.flush()
    g1 = Graduation(
        gym_id=1,
        modality_id=m.id,
        name="Branca",
        level=1,
        required_hours=Decimal("10"),
    )
    g2 = Graduation(
        gym_id=1,
        modality_id=m.id,
        name="Azul",
        level=2,
        required_hours=Decimal("20"),
    )
    db.add_all([g1, g2])
    db.flush()
    st = Student(user_id=user.id, nome="Aluno Treino", telefone="11999999999")
    db.add(st)
    db.flush()
    db.add(
        StudentModality(
            student_id=st.id,
            modality_id=m.id,
            graduation_id=g1.id,
            hours_trained=Decimal("0"),
        )
    )
    db.commit()
    db.refresh(st)
    db.refresh(m)
    return st, m


def test_training_and_progress(client, user_token, user, db):
    st, m = _training_setup(db, user)

    r = client.post(
        "/training",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"student_id": st.id, "modality_id": m.id, "hours": 2},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["data"]["total_xp"] == 10
    assert body["data"]["hours_trained"] == 2.0

    pr = client.get(
        f"/students/{st.id}/progress",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert pr.status_code == 200, pr.text
    items = pr.json()["data"]
    assert len(items) == 1
    assert items[0]["progress_percent"] == 20.0
    assert items[0]["eligible"] is False


def test_training_forbidden_other_student(client, user_token, user, admin_user, db):
    st, m = _training_setup(db, admin_user)

    r = client.post(
        "/training",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"student_id": st.id, "modality_id": m.id, "hours": 1},
    )
    assert r.status_code == 403


def test_graduate_and_gamification(client, admin_token, user, db):
    st, m = _training_setup(db, user)

    client.post(
        "/training",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"student_id": st.id, "modality_id": m.id, "hours": 10},
    )

    gr = client.post(
        f"/students/{st.id}/graduate",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"modality_id": m.id},
    )
    assert gr.status_code == 200, gr.text
    gdata = gr.json()["data"]
    assert gdata["new_level"] == 2
    assert BADGE_FIRST_GRADUATION in gdata["badges_unlocked"]

    prog = client.get(
        f"/students/{st.id}/progress",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert prog.status_code == 200
    row = prog.json()["data"][0]
    assert row["hours_trained"] == 0.0
    assert row["graduation_name"] == "Azul"

    gam = client.get(
        f"/students/{st.id}/gamification",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert gam.status_code == 200
    gbody = gam.json()["data"]
    assert gbody["total_xp"] == 110
    assert gbody["ranking_position"] == 1
    names = {b["name"] for b in gbody["badges"]}
    assert BADGE_FIRST_GRADUATION in names

    rk = client.get(
        "/ranking",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rk.status_code == 200
    top = rk.json()["data"]
    assert len(top) >= 1
    assert top[0]["student_id"] == st.id


def test_ranking_any_authenticated(client, user_token, user, db):
    _training_setup(db, user)
    rk = client.get(
        "/ranking",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert rk.status_code == 200
