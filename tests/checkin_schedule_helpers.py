"""Cria `GymClass` + `GymScheduleSlot` para testes de check-in na grade."""

from __future__ import annotations

from datetime import datetime, time

import pytz
from sqlalchemy.orm import Session

from app.models.gym_schedule import GymClass, GymScheduleSlot
from app.models.modality import Modality


def ensure_slot_for_checkin_tests(db: Session, *, gym_id: int = 1) -> int:
    m = db.query(Modality).filter(Modality.name == "Muay Thai").first()
    assert m is not None
    gc = db.query(GymClass).filter(GymClass.gym_id == gym_id).first()
    if gc is None:
        gc = GymClass(
            gym_id=gym_id,
            name="Aula Check-in Teste",
            modality_id=m.id,
            is_active=True,
        )
        db.add(gc)
        db.flush()
    elif gc.modality_id is None:
        gc.modality_id = m.id

    tz = pytz.timezone("America/Sao_Paulo")
    wd = int(datetime.now(tz).weekday())
    slot = (
        db.query(GymScheduleSlot)
        .filter(
            GymScheduleSlot.gym_id == gym_id,
            GymScheduleSlot.weekday == wd,
            GymScheduleSlot.gym_class_id == gc.id,
        )
        .first()
    )
    if slot is None:
        slot = GymScheduleSlot(
            gym_id=gym_id,
            gym_class_id=gc.id,
            weekday=wd,
            start_time=time(0, 0),
            end_time=time(23, 59),
            is_active=True,
        )
        db.add(slot)
    db.commit()
    db.refresh(slot)
    return int(slot.id)
