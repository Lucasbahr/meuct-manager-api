"""CRUD de aulas (`GymClass`) e grade semanal (`GymScheduleSlot`) por academia."""

from __future__ import annotations

from datetime import time
from typing import Any, List, Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.gym_schedule import GymClass, GymScheduleSlot
from app.models.modality import Modality
from app.schemas.gym_schedule import WEEKDAY_LABELS_PT, GymClassOut, GymScheduleSlotOut


def _time_str(t: time) -> str:
    return t.strftime("%H:%M")


def serialize_gym_class(row: GymClass) -> dict[str, Any]:
    return GymClassOut.model_validate(row).model_dump()


def serialize_schedule_slot(row: GymScheduleSlot) -> dict[str, Any]:
    wd = int(row.weekday)
    label = WEEKDAY_LABELS_PT[wd] if 0 <= wd <= 6 else str(wd)
    gc = row.gym_class
    if gc is None:
        raise HTTPException(status_code=500, detail="Slot sem aula associada")
    return {
        "id": row.id,
        "gym_id": row.gym_id,
        "weekday": wd,
        "weekday_label": label,
        "start_time": _time_str(row.start_time),
        "end_time": _time_str(row.end_time),
        "room": row.room,
        "notes": row.notes,
        "is_active": row.is_active,
        "class_info": serialize_gym_class(gc),
    }


def list_gym_classes(
    db: Session, gym_id: int, *, active_only: bool = False
) -> List[dict[str, Any]]:
    q = db.query(GymClass).filter(GymClass.gym_id == gym_id)
    if active_only:
        q = q.filter(GymClass.is_active.is_(True))
    rows = q.order_by(GymClass.sort_order.asc(), GymClass.name.asc()).all()
    return [serialize_gym_class(r) for r in rows]


def get_gym_class(db: Session, gym_id: int, class_id: int) -> GymClass:
    row = (
        db.query(GymClass)
        .filter(GymClass.id == class_id, GymClass.gym_id == gym_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Aula não encontrada")
    return row


def create_gym_class(
    db: Session,
    gym_id: int,
    *,
    name: str,
    description: Optional[str],
    modality_id: Optional[int],
    instructor_name: Optional[str],
    duration_minutes: Optional[int],
    sort_order: int,
    is_active: bool,
) -> GymClass:
    if modality_id is not None:
        if db.query(Modality).filter(Modality.id == modality_id).first() is None:
            raise HTTPException(status_code=400, detail="modalidade_id inválido")
    row = GymClass(
        gym_id=gym_id,
        name=name.strip(),
        description=description.strip() if description else None,
        modality_id=modality_id,
        instructor_name=instructor_name.strip() if instructor_name else None,
        duration_minutes=duration_minutes,
        sort_order=sort_order,
        is_active=is_active,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Já existe uma aula com este nome nesta academia",
        ) from e
    db.refresh(row)
    return row


def update_gym_class(
    db: Session,
    gym_id: int,
    class_id: int,
    patch: dict[str, Any],
) -> GymClass:
    row = get_gym_class(db, gym_id, class_id)
    if "name" in patch:
        row.name = str(patch["name"]).strip()
    if "description" in patch:
        v = patch["description"]
        row.description = v.strip() if isinstance(v, str) and v else None
    if "modality_id" in patch:
        mid = patch["modality_id"]
        if mid is not None:
            if db.query(Modality).filter(Modality.id == mid).first() is None:
                raise HTTPException(status_code=400, detail="modalidade_id inválido")
        row.modality_id = mid
    if "instructor_name" in patch:
        v = patch["instructor_name"]
        row.instructor_name = v.strip() if isinstance(v, str) and v else None
    if "duration_minutes" in patch:
        row.duration_minutes = patch["duration_minutes"]
    if "sort_order" in patch:
        row.sort_order = patch["sort_order"]
    if "is_active" in patch:
        row.is_active = bool(patch["is_active"])
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Já existe uma aula com este nome nesta academia",
        ) from e
    db.refresh(row)
    return row


def delete_gym_class(db: Session, gym_id: int, class_id: int) -> None:
    row = get_gym_class(db, gym_id, class_id)
    db.delete(row)
    db.flush()


def list_schedule_slots(
    db: Session, gym_id: int, *, active_only: bool = False
) -> List[dict[str, Any]]:
    q = (
        db.query(GymScheduleSlot)
        .join(GymClass, GymClass.id == GymScheduleSlot.gym_class_id)
        .options(joinedload(GymScheduleSlot.gym_class))
        .filter(GymScheduleSlot.gym_id == gym_id)
    )
    if active_only:
        q = q.filter(
            GymScheduleSlot.is_active.is_(True),
            GymClass.is_active.is_(True),
        )
    rows = q.order_by(
        GymScheduleSlot.weekday.asc(),
        GymScheduleSlot.start_time.asc(),
    ).all()
    return [serialize_schedule_slot(r) for r in rows]


def schedule_grouped_by_weekday(db: Session, gym_id: int, *, active_only: bool = True):
    flat = list_schedule_slots(db, gym_id, active_only=active_only)
    buckets: dict[int, list] = {i: [] for i in range(7)}
    for item in flat:
        buckets[item["weekday"]].append(item)
    out = []
    for wd in range(7):
        if buckets[wd]:
            out.append(
                {
                    "weekday": wd,
                    "weekday_label": WEEKDAY_LABELS_PT[wd],
                    "slots": buckets[wd],
                }
            )
    return out


def get_schedule_slot(db: Session, gym_id: int, slot_id: int) -> GymScheduleSlot:
    row = (
        db.query(GymScheduleSlot)
        .options(joinedload(GymScheduleSlot.gym_class))
        .filter(GymScheduleSlot.id == slot_id, GymScheduleSlot.gym_id == gym_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Horário não encontrado")
    return row


def create_schedule_slot(
    db: Session,
    gym_id: int,
    *,
    gym_class_id: int,
    weekday: int,
    start_time: time,
    end_time: time,
    room: Optional[str],
    notes: Optional[str],
    is_active: bool,
) -> GymScheduleSlot:
    gc = get_gym_class(db, gym_id, gym_class_id)
    if end_time <= start_time:
        raise HTTPException(
            status_code=400, detail="end_time deve ser posterior a start_time"
        )
    row = GymScheduleSlot(
        gym_id=gym_id,
        gym_class_id=gc.id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        room=room.strip() if room else None,
        notes=notes.strip() if notes else None,
        is_active=is_active,
    )
    db.add(row)
    db.flush()
    return get_schedule_slot(db, gym_id, row.id)


def update_schedule_slot(
    db: Session,
    gym_id: int,
    slot_id: int,
    patch: dict[str, Any],
) -> GymScheduleSlot:
    row = get_schedule_slot(db, gym_id, slot_id)
    if "gym_class_id" in patch:
        cid = patch["gym_class_id"]
        get_gym_class(db, gym_id, cid)
        row.gym_class_id = cid
    if "weekday" in patch:
        row.weekday = patch["weekday"]
    if "start_time" in patch:
        row.start_time = patch["start_time"]
    if "end_time" in patch:
        row.end_time = patch["end_time"]
    if "room" in patch:
        v = patch["room"]
        row.room = v.strip() if isinstance(v, str) and v else None
    if "notes" in patch:
        v = patch["notes"]
        row.notes = v.strip() if isinstance(v, str) and v else None
    if "is_active" in patch:
        row.is_active = bool(patch["is_active"])
    if row.end_time <= row.start_time:
        raise HTTPException(
            status_code=400, detail="end_time deve ser posterior a start_time"
        )
    db.flush()
    return get_schedule_slot(db, gym_id, slot_id)


def delete_schedule_slot(db: Session, gym_id: int, slot_id: int) -> None:
    row = get_schedule_slot(db, gym_id, slot_id)
    db.delete(row)
    db.flush()
