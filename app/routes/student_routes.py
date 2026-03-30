from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.schemas.response import ResponseBase
from app.core.deps import get_current_user, require_admin
from app.db.deps import get_db
from app.models.student import Student
from app.models.checkin import Checkin
from app.models.user import User
from app.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentAdminUpdate,
    StudentResponse,
)
from app.services.student_photo import (
    delete_student_photo,
    get_photo_bytes,
    save_student_photo,
)

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
        e_atleta=data.e_atleta,
        cartel_mma=data.cartel_mma,
        cartel_jiu=data.cartel_jiu,
        cartel_k1=data.cartel_k1,
        nivel_competicao=data.nivel_competicao,
        link_tapology=data.link_tapology,
        data_nascimento=data.data_nascimento,
        ultima_luta_em=data.ultima_luta_em,
        ultima_luta_modalidade=data.ultima_luta_modalidade,
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

    updatable = (
        set(Student.__table__.columns.keys())
        - {"id", "user_id", "created_at", "updated_at", "foto_path"}
    )
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400, detail="Nenhum campo enviado para atualização"
        )
    for field, value in update_data.items():
        if field not in updatable:
            raise HTTPException(status_code=400, detail=f"Campo inválido: {field}")
        setattr(student, field, value)
    student.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(student)

    return {
        "success": True,
        "message": "Perfil atualizado",
        "data": StudentResponse.model_validate(student),
    }


@router.post("/me/photo", response_model=ResponseBase)
async def upload_my_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    student = (
        db.query(Student).filter(Student.user_id == current_user["user_id"]).first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    content = await file.read()
    old = student.foto_path
    student.foto_path = save_student_photo(
        student.id, content, file.content_type or ""
    )
    delete_student_photo(old)
    student.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(student)
    return {
        "success": True,
        "message": "Foto atualizada",
        "data": StudentResponse.model_validate(student),
    }


@router.get("/me/photo")
def get_my_photo(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    student = (
        db.query(Student).filter(Student.user_id == current_user["user_id"]).first()
    )
    if not student or not student.foto_path:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    content, media_type = get_photo_bytes(student.foto_path)
    return Response(content=content, media_type=media_type)


@router.get("/{student_id}/photo")
def get_student_photo(
    student_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student or not student.foto_path:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    if user.get("role") != "ADMIN":
        mine = db.query(Student).filter(Student.user_id == user["user_id"]).first()
        if not mine or mine.id != student_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    content, media_type = get_photo_bytes(student.foto_path)
    return Response(content=content, media_type=media_type)


@router.post("/{student_id}/photo", response_model=ResponseBase)
async def admin_upload_student_photo(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    content = await file.read()
    old = student.foto_path
    student.foto_path = save_student_photo(
        student.id, content, file.content_type or ""
    )
    delete_student_photo(old)
    student.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(student)
    return {
        "success": True,
        "message": "Foto do aluno atualizada",
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


@router.delete("/{student_id}", response_model=ResponseBase)
def admin_delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Remove dependent rows first (no cascade configured).
    db.query(Checkin).filter(Checkin.student_id == student.id).delete(
        synchronize_session=False
    )

    # Remove stored photo (local or GCS depending on env).
    delete_student_photo(student.foto_path)

    user = db.query(User).filter(User.id == student.user_id).first()
    db.delete(student)
    if user:
        db.delete(user)

    db.commit()

    return {
        "success": True,
        "message": "Aluno e usuário removidos",
        "data": None,
    }
