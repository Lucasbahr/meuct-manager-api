"""GET /dashboard/analytics — alunos e receita (produtos + mensalidades)."""

from datetime import datetime, timezone
from decimal import Decimal

from app.models.plan import Plan, StudentSubscription, SubscriptionPayment
from app.models.student import Student
from app.services.user_service import create_user


def test_dashboard_analytics_students_and_revenue(client, db, admin_token):
    """Alunos por status, novos no mês vs anterior; receita produtos + mensalidades."""
    from app.models.marketplace import ShopOrder
    from app.services import marketplace_service as msvc

    ref_y, ref_m = 2024, 6
    # Junho 2024 (SP) — limites já testados indiretamente pelo serviço
    june_mid = datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc)
    may_mid = datetime(2024, 5, 10, 12, 0, 0, tzinfo=timezone.utc)

    u1 = create_user(db, "dash_a1@test.com", "123456", role="ALUNO", gym_id=1)
    u2 = create_user(db, "dash_a2@test.com", "123456", role="ALUNO", gym_id=1)
    u3 = create_user(db, "dash_a3@test.com", "123456", role="ALUNO", gym_id=1)

    s1 = Student(user_id=u1.id, nome="A1", status="ativo", created_at=june_mid)
    s2 = Student(user_id=u2.id, nome="A2", status="ATIVO", created_at=may_mid)
    s3 = Student(user_id=u3.id, nome="A3", status="inativo", created_at=may_mid)
    db.add_all([s1, s2, s3])
    db.commit()

    plan = Plan(
        gym_id=1,
        name="Plano Teste",
        price=Decimal("100.00"),
        duration_days=30,
        is_active=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    sub = StudentSubscription(
        student_id=s1.id,
        plan_id=plan.id,
        start_date=june_mid.date(),
        end_date=june_mid.date(),
        status="active",
        created_at=june_mid,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    pay = SubscriptionPayment(
        student_id=s1.id,
        subscription_id=sub.id,
        amount=Decimal("100.00"),
        status="paid",
        due_date=june_mid.date(),
        paid_at=june_mid,
        created_at=june_mid,
    )
    db.add(pay)
    db.commit()

    stu = db.query(Student).filter(Student.user_id == u1.id).first()
    order = ShopOrder(
        gym_id=1,
        student_id=stu.id,
        total_amount=Decimal("50.00"),
        status=msvc.ORDER_PAID,
        created_at=june_mid,
    )
    db.add(order)
    db.commit()

    r = client.get(
        f"/dashboard/analytics?year={ref_y}&month={ref_m}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    d = body["data"]
    assert d["reference_year"] == ref_y
    assert d["reference_month"] == ref_m
    assert d["students"]["total"] == 3
    assert d["students"]["active"] == 2
    assert d["students"]["inactive"] == 1
    assert d["students"]["new_in_reference_month"] == 1
    assert d["students"]["new_in_previous_month"] == 2
    assert d["revenue"]["products"]["reference_month"]["total"] == 50.0
    assert d["revenue"]["memberships"]["reference_month"]["total"] == 100.0
    assert d["revenue"]["combined"]["reference_month_total"] == 150.0


def test_dashboard_analytics_forbidden_for_student(client, user_token):
    r = client.get(
        "/dashboard/analytics",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 403


def test_dashboard_analytics_invalid_month(client, admin_token):
    r = client.get(
        "/dashboard/analytics?month=13",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422
