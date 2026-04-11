from fastapi import status


def test_admin_delete_user_removes_student_and_checkins(client, admin_token, db):
    from app.models.user import User
    from app.models.student import Student
    from app.models.checkin import Checkin

    user = User(
        gym_id=1,
        email="x@test.com",
        password="pw",
        role="ALUNO",
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    student = Student(user_id=user.id, nome="Aluno")
    db.add(student)
    db.commit()
    db.refresh(student)

    checkin = Checkin(student_id=student.id)
    db.add(checkin)
    db.commit()

    resp = client.delete(
        f"/admin/users/{user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK

    assert db.query(User).filter(User.id == user.id).first() is None
    assert db.query(Student).filter(Student.user_id == user.id).first() is None
    assert db.query(Checkin).filter(Checkin.student_id == student.id).count() == 0

