from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.deps import get_db
from app.models.checkin import Checkin
from app.models.student import Student
from app.models.user import User
from app.schemas.response import ResponseBase
from app.services.student_photo import delete_student_photo

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.delete("/users/{user_id}", response_model=ResponseBase)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    student = db.query(Student).filter(Student.user_id == user_id).first()
    if student:
        db.query(Checkin).filter(Checkin.student_id == student.id).delete(
            synchronize_session=False
        )
        delete_student_photo(student.foto_path)
        db.delete(student)

    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": "User removido",
        "data": None,
    }

