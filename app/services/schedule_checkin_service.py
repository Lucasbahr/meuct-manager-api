"""Check-in vinculado a `GymScheduleSlot`: validação e cálculo de horas."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytz
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.checkin import Checkin
from app.models.gym_schedule import GymClass, GymScheduleSlot


def load_active_slot(db: Session, gym_id: int, slot_id: int) -> tuple[GymScheduleSlot, GymClass]:
    slot = (
        db.query(GymScheduleSlot)
        .options(joinedload(GymScheduleSlot.gym_class))
        .filter(
            GymScheduleSlot.id == slot_id,
            GymScheduleSlot.gym_id == gym_id,
        )
        .first()
    )
    if slot is None or not slot.is_active:
        raise HTTPException(
            status_code=404,
            detail="Horário da grade não encontrado ou inativo",
        )
    gc = slot.gym_class
    if gc is None or not gc.is_active:
        raise HTTPException(
            status_code=400,
            detail="Aula deste horário está indisponível",
        )
    if gc.modality_id is None:
        raise HTTPException(
            status_code=400,
            detail="Vincule uma modalidade à aula na grade para liberar check-in e horas",
        )
    return slot, gc


def slot_duration_hours(slot: GymScheduleSlot, gym_class: GymClass) -> Decimal:
    """Horas creditadas: duração do intervalo na grade; reforça `duration_minutes` se maior."""
    a = datetime.combine(date.min, slot.end_time)
    b = datetime.combine(date.min, slot.start_time)
    secs = (a - b).total_seconds()
    h = Decimal(str(round(max(0.0, secs) / 3600, 4)))
    if gym_class.duration_minutes:
        dm = Decimal(str(gym_class.duration_minutes)) / Decimal(60)
        h = max(h, dm)
    if h <= 0:
        h = Decimal("1")
    return h


def assert_self_checkin_time_window(slot: GymScheduleSlot) -> None:
    """Aluno: mesmo dia da semana da grade e janela em torno do horário da aula."""
    tz = pytz.timezone("America/Sao_Paulo")
    now = datetime.now(tz)
    if int(now.weekday()) != int(slot.weekday):
        raise HTTPException(
            status_code=400,
            detail="Este horário da grade não corresponde ao dia de hoje",
        )
    d = now.date()
    start_dt = tz.localize(datetime.combine(d, slot.start_time))
    end_dt = tz.localize(datetime.combine(d, slot.end_time))
    if end_dt <= start_dt:
        end_dt = end_dt + timedelta(days=1)
    margin_before = timedelta(minutes=45)
    margin_after = timedelta(minutes=90)
    if not (start_dt - margin_before <= now <= end_dt + margin_after):
        raise HTTPException(
            status_code=400,
            detail="Check-in só é permitido próximo ao horário desta aula",
        )


def today_utc_range_sao_paulo() -> tuple[datetime, datetime]:
    tz = pytz.timezone("America/Sao_Paulo")
    local_now = datetime.now(tz)
    day_start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end_local = day_start_local + timedelta(days=1)
    return (
        day_start_local.astimezone(timezone.utc).replace(tzinfo=None),
        day_end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def has_checkin_for_slot_today(
    db: Session, student_id: int, slot_id: int
) -> bool:
    start_utc, end_utc = today_utc_range_sao_paulo()
    return (
        db.query(Checkin.id)
        .filter(
            Checkin.student_id == student_id,
            Checkin.gym_schedule_slot_id == slot_id,
            Checkin.created_at >= start_utc,
            Checkin.created_at < end_utc,
        )
        .first()
        is not None
    )
