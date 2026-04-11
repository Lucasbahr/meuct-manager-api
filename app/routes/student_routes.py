from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session, selectinload
from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.response import ResponseBase
from app.core.deps import (
    get_current_user,
    require_academy_admin,
    require_gym_id,
    require_staff,
)
from app.core.roles import is_staff, normalize_role
from app.db.deps import get_db
from app.models.student import Student
from app.models.student_modality import StudentModality as StudentModalityRow
from app.models.checkin import Checkin
from app.models.user import User
from app.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentAdminUpdate,
)
from app.schemas.membership import StudentAlertItem, StudentsAlertsOut
from app.services import membership_service as membership_svc
from app.services.student_photo import (
    delete_student_photo,
    get_photo_bytes,
    save_student_athlete_card_photo,
    save_student_photo,
)
from app.services import student_modality_service as sm_svc

router = APIRouter(prefix="/students", tags=["Students"])


#  ADMIN - lista todos
@router.get("/", response_model=ResponseBase)
def list_students(
    status: Optional[str] = None,
    user=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    query = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(User.gym_id == gym_id)
        .options(
            selectinload(Student.student_modalities).selectinload(
                StudentModalityRow.modality
            ),
            selectinload(Student.student_modalities).selectinload(
                StudentModalityRow.graduation
            ),
        )
    )
    if status:
        query = query.filter(Student.status == status)

    students = query.all()
    return {
        "success": True,
        "message": "Lista de alunos",
        "data": [sm_svc.student_to_response(s).model_dump() for s in students],
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

    owner = db.query(User).filter(User.id == user["user_id"]).first()
    if owner and owner.gym_id is not None:
        if data.modality_id is not None and data.graduation_id is not None:
            sm_svc.add_student_modality(
                db,
                owner.gym_id,
                student_id=student.id,
                modality_id=data.modality_id,
                graduation_id=data.graduation_id,
                hours_trained=Decimal("0"),
            )
        else:
            sm_svc.ensure_default_enrollment(db, owner.gym_id, student.id)
        db.commit()

    loaded = sm_svc.load_student_with_modalities(db, student.id) or student
    return {
        "success": True,
        "message": "Aluno criado com sucesso",
        "data": sm_svc.student_to_response(loaded).model_dump(),
    }


#  Get do Usuario
@router.get("/me", response_model=ResponseBase)
def get_my_student(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    student = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.user_id == user["user_id"], User.gym_id == gym_id)
        .first()
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    loaded = sm_svc.load_student_with_modalities(db, student.id) or student
    return {
        "success": True,
        "message": "Dados do aluno",
        "data": sm_svc.student_to_response(loaded).model_dump(),
    }


@router.get("/athletes", response_model=ResponseBase)
def list_athletes_directory(
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    """
    Lista alunos com `e_atleta=True` para a aba **Atletas** do app.
    Qualquer usuário autenticado (aluno ou admin); não expõe edição.
    """
    students = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.e_atleta.is_(True), User.gym_id == gym_id)
        .options(
            selectinload(Student.student_modalities).selectinload(
                StudentModalityRow.modality
            ),
            selectinload(Student.student_modalities).selectinload(
                StudentModalityRow.graduation
            ),
        )
        .order_by(Student.nome.asc())
        .all()
    )
    return {
        "success": True,
        "message": "Atletas",
        "data": [sm_svc.student_to_response(s).model_dump() for s in students],
    }


@router.get("/alerts", response_model=ResponseBase)
def students_subscription_alerts(
    _staff=Depends(require_staff),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    raw = membership_svc.build_students_alerts(db, gym_id)
    out = StudentsAlertsOut(
        due_soon=[StudentAlertItem(**x) for x in raw["due_soon"]],
        overdue=[StudentAlertItem(**x) for x in raw["overdue"]],
    )
    return {
        "success": True,
        "message": "Alertas de vencimento e atraso (mensalidades)",
        "data": out.model_dump(),
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
        - {
            "id",
            "user_id",
            "created_at",
            "updated_at",
            "foto_path",
            "foto_atleta_path",
        }
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
    loaded = sm_svc.load_student_with_modalities(db, student.id) or student
    return {
        "success": True,
        "message": "Perfil atualizado",
        "data": sm_svc.student_to_response(loaded).model_dump(),
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
    owner = db.query(User).filter(User.id == student.user_id).first()
    if not owner or owner.gym_id is None:
        raise HTTPException(
            status_code=400, detail="Usuário sem gym associado; não é possível enviar foto"
        )
    content = await file.read()
    old = student.foto_path
    student.foto_path = save_student_photo(
        owner.gym_id, student.id, content, file.content_type or ""
    )
    delete_student_photo(old)
    student.updated_at = datetime.now(timezone.utc)
    db.commit()
    loaded = sm_svc.load_student_with_modalities(db, student.id) or student
    return {
        "success": True,
        "message": "Foto atualizada",
        "data": sm_svc.student_to_response(loaded).model_dump(),
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


@router.get("/{student_id}/athlete-card/photo")
def get_student_athlete_card_photo(
    student_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    gym_id: int = Depends(require_gym_id),
):
    student = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.id == student_id, User.gym_id == gym_id)
        .first()
    )
    if not student or not student.foto_atleta_path:
        raise HTTPException(status_code=404, detail="Foto do cartão não encontrada")
    if not is_staff(normalize_role(user.get("role"))):
        if not student.e_atleta:
            raise HTTPException(status_code=403, detail="Not authorized")
    content, media_type = get_photo_bytes(student.foto_atleta_path)
    return Response(content=content, media_type=media_type)


@router.post("/{student_id}/athlete-card/photo", response_model=ResponseBase)
async def admin_upload_student_athlete_card_photo(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _staff=Depends(require_staff),
    gym_id: int = Depends(require_gym_id),
):
    student = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.id == student_id, User.gym_id == gym_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    content = await file.read()
    old = student.foto_atleta_path
    student.foto_atleta_path = save_student_athlete_card_photo(
        gym_id, student.id, content, file.content_type or ""
    )
    delete_student_photo(old)
    student.updated_at = datetime.now(timezone.utc)
    db.commit()
    loaded = sm_svc.load_student_with_modalities(db, student.id) or student
    return {
        "success": True,
        "message": "Foto do cartão do atleta atualizada",
        "data": sm_svc.student_to_response(loaded).model_dump(),
    }


@router.get("/{student_id}/modalities", response_model=ResponseBase)
def list_student_modalities_endpoint(
    student_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    gym_id: int = Depends(require_gym_id),
):
    from app.services import training_service as training_svc

    training_svc.can_access_student_training(db, user, student_id, gym_id)
    items = sm_svc.list_student_modalities_items(db, gym_id, student_id)
    return {
        "success": True,
        "message": "Modalidades do aluno",
        "data": [i.model_dump() for i in items],
    }


@router.get("/{student_id}/photo")
def get_student_photo(
    student_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    gym_id: int = Depends(require_gym_id),
):
    student = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.id == student_id, User.gym_id == gym_id)
        .first()
    )
    if not student or not student.foto_path:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    if not is_staff(normalize_role(user.get("role"))):
        if student.user_id != user["user_id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    content, media_type = get_photo_bytes(student.foto_path)
    return Response(content=content, media_type=media_type)


@router.post("/{student_id}/photo", response_model=ResponseBase)
async def admin_upload_student_photo(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _staff=Depends(require_staff),
    gym_id: int = Depends(require_gym_id),
):
    student = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.id == student_id, User.gym_id == gym_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    content = await file.read()
    old = student.foto_path
    student.foto_path = save_student_photo(
        gym_id, student.id, content, file.content_type or ""
    )
    delete_student_photo(old)
    student.updated_at = datetime.now(timezone.utc)
    db.commit()
    loaded = sm_svc.load_student_with_modalities(db, student.id) or student
    return {
        "success": True,
        "message": "Foto do aluno atualizada",
        "data": sm_svc.student_to_response(loaded).model_dump(),
    }


# ADMIN atualiza aluno
@router.put("/{student_id}", response_model=ResponseBase)
def admin_update_student(
    student_id: int,
    data: StudentAdminUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_staff),
    gym_id: int = Depends(require_gym_id),
):
    student = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.id == student_id, User.gym_id == gym_id)
        .first()
    )

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
    loaded = sm_svc.load_student_with_modalities(db, student.id) or student
    return {
        "success": True,
        "message": "Aluno atualizado",
        "data": sm_svc.student_to_response(loaded).model_dump(),
    }


@router.delete("/{student_id}", response_model=ResponseBase)
def admin_delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_academy_admin),
    gym_id: int = Depends(require_gym_id),
):
    student = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.id == student_id, User.gym_id == gym_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Remove dependent rows first (no cascade configured).
    db.query(Checkin).filter(Checkin.student_id == student.id).delete(
        synchronize_session=False
    )

    # Remove stored photos (local or GCS depending on env).
    delete_student_photo(student.foto_path)
    delete_student_photo(student.foto_atleta_path)

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
