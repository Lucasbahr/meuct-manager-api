from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.student import Student


def _student_for_user(db: Session, user_id: int) -> Student:
    s = db.query(Student).filter(Student.user_id == user_id).first()
    if s is None:
        s = Student(user_id=user_id, nome="Aluno Teste", telefone="11999999999")
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def test_membership_plans_subscriptions_pay_and_reports(client, admin_token, user, db):
    h = {"Authorization": f"Bearer {admin_token}"}
    st = _student_for_user(db, user.id)

    r = client.post(
        "/plans",
        headers=h,
        json={
            "name": "Mensal",
            "price": "120.00",
            "duration_days": 30,
            "is_active": True,
        },
    )
    assert r.status_code == 200, r.text
    plan_id = r.json()["data"]["id"]

    lst = client.get("/plans", headers=h)
    assert lst.status_code == 200
    assert len(lst.json()["data"]) >= 1

    sub_r = client.post(
        "/subscriptions",
        headers=h,
        json={"student_id": st.id, "plan_id": plan_id},
    )
    assert sub_r.status_code == 200, sub_r.text
    pay_id = sub_r.json()["data"]["payments"][0]["id"]

    dup = client.post(
        "/subscriptions",
        headers=h,
        json={"student_id": st.id, "plan_id": plan_id},
    )
    assert dup.status_code == 400

    pay = client.post(f"/payments/{pay_id}/pay", headers=h)
    assert pay.status_code == 200, pay.text
    assert pay.json()["data"]["status"] == "paid"

    fin = client.get("/reports/financial?days=30", headers=h)
    assert fin.status_code == 200, fin.text
    assert Decimal(fin.json()["data"]["total_received"]) > 0

    rev = client.get("/reports/revenue?days=30", headers=h)
    assert rev.status_code == 200
    assert isinstance(rev.json()["data"], list)

    plans_rep = client.get("/reports/plans?days=30&sort_by=revenue_paid", headers=h)
    assert plans_rep.status_code == 200
    assert len(plans_rep.json()["data"]) >= 1

    stud_rep = client.get("/reports/students", headers=h)
    assert stud_rep.status_code == 200
    assert stud_rep.json()["data"]["total_students"] >= 1

    alerts = client.get("/students/alerts", headers=h)
    assert alerts.status_code == 200
    body = alerts.json()["data"]
    assert "due_soon" in body and "overdue" in body


def test_membership_overdue_and_alerts(client, admin_token, user, db):
    from app.models.plan import Plan, StudentSubscription, SubscriptionPayment

    h = {"Authorization": f"Bearer {admin_token}"}
    st = _student_for_user(db, user.id)

    plan = Plan(gym_id=1, name="Trimestral", price="300.00", duration_days=90, is_active=True)
    db.add(plan)
    db.commit()
    db.refresh(plan)

    start = date.today() - timedelta(days=10)
    end = start + timedelta(days=90)
    sub = StudentSubscription(
        student_id=st.id,
        plan_id=plan.id,
        start_date=start,
        end_date=end,
        status="active",
    )
    db.add(sub)
    db.flush()
    pay = SubscriptionPayment(
        student_id=st.id,
        subscription_id=sub.id,
        amount=plan.price,
        status="pending",
        due_date=start,
    )
    db.add(pay)
    db.commit()

    alerts = client.get("/students/alerts", headers=h)
    assert alerts.status_code == 200
    overdue = alerts.json()["data"]["overdue"]
    assert any(x.get("reason") == "pagamento_atrasado" for x in overdue)
