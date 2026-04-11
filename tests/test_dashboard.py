def test_dashboard_me_includes_login_audit(client, user_token, user, db):
    from app.models.student import Student
    from app.services import student_modality_service as sm_svc

    st = Student(user_id=user.id, nome="Aluno", telefone="+5511999999999")
    db.add(st)
    db.commit()
    db.refresh(st)
    sm_svc.ensure_default_enrollment(db, 1, st.id)
    db.commit()

    r = client.get(
        "/dashboard/me", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    data = body["data"]
    assert data["usuario"]["email"] == "user@test.com"
    assert data["usuario"]["ultimo_login_em"] is not None
    assert data["checkins"] is not None
    actions = [a["action"] for a in data["minhas_acoes_recentes"]]
    assert "LOGIN" in actions


def test_dashboard_academy_shows_checkin_audit(client, admin_token, user, db):
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

    chk = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"student_id": student.id, "schedule_slot_id": sid},
    )
    assert chk.status_code == 200

    r = client.get(
        "/dashboard/academy", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["resumo"]["checkins_hoje"] >= 1
    actions = [e["action"] for e in data["auditoria"]]
    assert "CHECKIN" in actions
    assert any("actor_email" in e for e in data["auditoria"])


def test_dashboard_academy_forbidden_for_aluno(client, user_token):
    r = client.get(
        "/dashboard/academy", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert r.status_code == 403
