from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.schemas.response import ResponseBase
from app.core.deps import get_current_user, require_admin
from app.db.deps import get_db
from app.models.student import Student
from app.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentAdminUpdate,
    StudentResponse,
)
from typing import Optional

router = APIRouter(prefix="/students", tags=["Students"])


#  ADMIN - lista todos
@router.get("/", response_model=ResponseBase)
def list_students(
    status: Optional[str] = None,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Student)
    if status:
        query = query.filter(Student.status == status)

    students = query.all()
    return {
        "success": True,
        "message": "Lista de alunos",
        "data": [StudentResponse.model_validate(s) for s in students],
    }


#  criar usuario manual caso nao seja criado automatico
@router.post("/", response_model=ResponseBase)
def create_student(
    data: StudentCreate, user=Depends(get_current_user), db: Session = Depends(get_db)
):
    existing = db.query(Student).filter(Student.user_id == user["user_id"]).first()

    if existing:
        raise HTTPException(status_code=400, detail="Student already exists")

    student = Student(
        user_id=user["user_id"],
        nome=data.nome,
        telefone=data.telefone,
        modalidade=data.modalidade,
        graduacao=data.graduacao,
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    return {
        "success": True,
        "message": "Aluno criado com sucesso",
        "data": StudentResponse.model_validate(student),
    }


#  Get do Usuario
@router.get("/me", response_model=ResponseBase)
def get_my_student(user=Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.user_id == user["user_id"]).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return {
        "success": True,
        "message": "Dados do aluno",
        "data": StudentResponse.model_validate(student),
    }


#  Atualiza proprio perfil
@router.put("/me", response_model=ResponseBase)
def update_my_profile(
    data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    student = (
        db.query(Student).filter(Student.user_id == current_user["user_id"]).first()
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student.nome = data.nome
    student.telefone = data.telefone
    student.endereco = data.endereco
    student.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(student)

    return {
        "success": True,
        "message": "Perfil atualizado",
        "data": StudentResponse.model_validate(student),
    }


# ADMIN atualiza aluno
@router.put("/{student_id}", response_model=ResponseBase)
def admin_update_student(
    student_id: int,
    data: StudentAdminUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    valid_fields = Student.__table__.columns.keys()
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field not in valid_fields:
            raise HTTPException(status_code=400, detail=f"Campo inválido: {field}")
        setattr(student, field, value)
    if not update_data:
        raise HTTPException(
            status_code=400, detail="Nenhum campo válido enviado para atualização"
        )
    student.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(student)

    return {
        "success": True,
        "message": "Aluno atualizado",
        "data": StudentResponse.model_validate(student),
    }
