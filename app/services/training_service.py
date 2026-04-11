from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.gamification_constants import (
    BADGE_FIRST_GRADUATION,
    BADGE_STREAK_7,
    BADGE_WARRIOR_100,
    XP_PER_GRADUATION,
    XP_PER_TRAINING,
    XP_SOURCE_GRADUATION,
    XP_SOURCE_TRAINING,
    calculate_level,
)
from app.core.roles import is_staff
from app.models.gamification import Badge, StudentBadge, StudentStats, XpLog
from app.models.graduation import Graduation
from app.models.student import Student
from app.models.student_graduation_history import StudentGraduationHistory
from app.models.student_modality import StudentModality
from app.models.user import User


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def get_or_create_stats(db: Session, student_id: int) -> StudentStats:
    row = db.query(StudentStats).filter(StudentStats.student_id == student_id).first()
    if row:
        return row
    row = StudentStats(
        student_id=student_id,
        total_xp=0,
        level=0,
        current_streak=0,
        best_streak=0,
        training_sessions_count=0,
    )
    db.add(row)
    db.flush()
    return row


def assert_student_in_gym(db: Session, student_id: int, gym_id: int) -> Student:
    st = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.id == student_id, User.gym_id == gym_id)
        .first()
    )
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")
    return st


def can_access_student_training(
    db: Session,
    token_user: dict,
    student_id: int,
    gym_id: int,
) -> Student:
    st = assert_student_in_gym(db, student_id, gym_id)
    if is_staff(token_user.get("role")):
        return st
    if token_user.get("user_id") != st.user_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return st


def get_student_modality_row(
    db: Session, student_id: int, modality_id: int
) -> Optional[StudentModality]:
    return (
        db.query(StudentModality)
        .filter(
            StudentModality.student_id == student_id,
            StudentModality.modality_id == modality_id,
        )
        .first()
    )


def check_graduation_eligibility(sm: StudentModality) -> bool:
    req = sm.graduation.required_hours
    return Decimal(str(sm.hours_trained or 0)) >= Decimal(str(req))


def get_next_graduation(db: Session, sm: StudentModality) -> Optional[Graduation]:
    cur = sm.graduation
    return (
        db.query(Graduation)
        .filter(
            Graduation.gym_id == cur.gym_id,
            Graduation.modality_id == sm.modality_id,
            Graduation.level == cur.level + 1,
        )
        .first()
    )


def add_xp(db: Session, student_id: int, amount: int, source: str) -> StudentStats:
    stats = get_or_create_stats(db, student_id)
    stats.total_xp += amount
    stats.level = calculate_level(stats.total_xp)
    log = XpLog(student_id=student_id, amount=amount, source=source)
    db.add(log)
    return stats


def update_streak(db: Session, student_id: int) -> StudentStats:
    stats = get_or_create_stats(db, student_id)
    today = _today_utc()
    last = stats.last_training_date

    if last is None:
        stats.current_streak = 1
    elif last == today:
        pass
    elif last == today - timedelta(days=1):
        stats.current_streak += 1
    else:
        stats.current_streak = 1

    stats.last_training_date = today
    stats.best_streak = max(stats.best_streak or 0, stats.current_streak or 0)
    return stats


def unlock_badge(db: Session, student_id: int, badge_name: str) -> bool:
    badge = db.query(Badge).filter(Badge.name == badge_name).first()
    if not badge:
        return False
    exists = (
        db.query(StudentBadge)
        .filter(
            StudentBadge.student_id == student_id,
            StudentBadge.badge_id == badge.id,
        )
        .first()
    )
    if exists:
        return False
    db.add(StudentBadge(student_id=student_id, badge_id=badge.id))
    return True


def add_training(
    db: Session,
    student_id: int,
    modality_id: int,
    hours: Decimal,
    gym_id: int,
) -> dict[str, Any]:
    if hours <= 0:
        raise HTTPException(status_code=400, detail="hours must be positive")

    sm = get_student_modality_row(db, student_id, modality_id)
    if not sm:
        raise HTTPException(
            status_code=400,
            detail="Student is not enrolled in this modality",
        )

    if sm.graduation.gym_id != gym_id:
        raise HTTPException(status_code=400, detail="Modality/graduation mismatch gym")

    sm.hours_trained = Decimal(str(sm.hours_trained or 0)) + hours

    stats = update_streak(db, student_id)
    stats.training_sessions_count += 1
    add_xp(db, student_id, XP_PER_TRAINING, XP_SOURCE_TRAINING)

    unlocked: list[str] = []
    if stats.current_streak >= 7 and unlock_badge(db, student_id, BADGE_STREAK_7):
        unlocked.append(BADGE_STREAK_7)
    if stats.training_sessions_count >= 100 and unlock_badge(
        db, student_id, BADGE_WARRIOR_100
    ):
        unlocked.append(BADGE_WARRIOR_100)

    db.flush()
    db.refresh(sm)
    db.refresh(stats)

    return {
        "hours_trained": float(sm.hours_trained),
        "total_xp": stats.total_xp,
        "level": stats.level,
        "current_streak": stats.current_streak,
        "badges_unlocked": unlocked,
        "eligible_for_graduation": check_graduation_eligibility(sm),
    }


def graduate_student(
    db: Session, student_id: int, modality_id: int, gym_id: int
) -> dict[str, Any]:
    sm = get_student_modality_row(db, student_id, modality_id)
    if not sm:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if sm.graduation.gym_id != gym_id:
        raise HTTPException(status_code=400, detail="Invalid gym for graduation")

    if not check_graduation_eligibility(sm):
        raise HTTPException(
            status_code=400,
            detail="Not enough hours for next graduation",
        )

    nxt = get_next_graduation(db, sm)
    if not nxt:
        raise HTTPException(
            status_code=400,
            detail="No next graduation level defined for this modality",
        )

    hours_snap = Decimal(str(sm.hours_trained or 0))
    hist_before = (
        db.query(func.count(StudentGraduationHistory.id))
        .filter(StudentGraduationHistory.student_id == student_id)
        .scalar()
        or 0
    )

    db.add(
        StudentGraduationHistory(
            student_id=student_id,
            modality_id=modality_id,
            graduation_id=sm.graduation_id,
            hours_when_achieved=hours_snap,
        )
    )

    sm.graduation_id = nxt.id
    sm.hours_trained = Decimal(0)

    add_xp(db, student_id, XP_PER_GRADUATION, XP_SOURCE_GRADUATION)
    stats = get_or_create_stats(db, student_id)
    stats.level = calculate_level(stats.total_xp)

    unlocked: list[str] = []
    if hist_before == 0 and unlock_badge(db, student_id, BADGE_FIRST_GRADUATION):
        unlocked.append(BADGE_FIRST_GRADUATION)

    db.flush()
    db.refresh(sm)

    return {
        "new_graduation_id": nxt.id,
        "new_graduation_name": nxt.name,
        "new_level": nxt.level,
        "badges_unlocked": unlocked,
        "total_xp": stats.total_xp,
        "level": stats.level,
    }


def progress_for_modality(db: Session, sm: StudentModality) -> dict[str, Any]:
    g = sm.graduation
    req = float(g.required_hours)
    cur = float(sm.hours_trained or 0)
    pct = min(100.0, (cur / req * 100) if req > 0 else 0.0)
    return {
        "modality_id": sm.modality_id,
        "modality_name": sm.modality.name,
        "graduation_id": g.id,
        "graduation_name": g.name,
        "level": g.level,
        "hours_trained": cur,
        "required_hours": req,
        "progress_percent": round(pct, 2),
        "eligible": check_graduation_eligibility(sm),
    }


def student_progress(
    db: Session, student_id: int, modality_id: Optional[int], gym_id: int
) -> list[dict[str, Any]]:
    assert_student_in_gym(db, student_id, gym_id)
    q = (
        db.query(StudentModality)
        .join(Graduation, Graduation.id == StudentModality.graduation_id)
        .filter(StudentModality.student_id == student_id, Graduation.gym_id == gym_id)
    )
    if modality_id is not None:
        q = q.filter(StudentModality.modality_id == modality_id)
    rows = q.all()
    if modality_id is not None and not rows:
        raise HTTPException(status_code=404, detail="Modality enrollment not found")
    return [progress_for_modality(db, sm) for sm in rows]


def gamification_snapshot(db: Session, student_id: int, gym_id: int) -> dict[str, Any]:
    assert_student_in_gym(db, student_id, gym_id)
    stats = get_or_create_stats(db, student_id)
    db.flush()
    db.refresh(stats)

    badges = (
        db.query(StudentBadge, Badge)
        .join(Badge, Badge.id == StudentBadge.badge_id)
        .filter(StudentBadge.student_id == student_id)
        .all()
    )

    rank = ranking_position(db, student_id, gym_id)

    return {
        "total_xp": stats.total_xp,
        "level": stats.level,
        "current_streak": stats.current_streak,
        "best_streak": stats.best_streak,
        "training_sessions_count": stats.training_sessions_count,
        "last_training_date": (
            stats.last_training_date.isoformat() if stats.last_training_date else None
        ),
        "badges": [
            {
                "name": b.name,
                "description": b.description,
                "icon": b.icon,
                "unlocked_at": sb.unlocked_at.isoformat() if sb.unlocked_at else None,
            }
            for sb, b in badges
        ],
        "ranking_position": rank,
    }


def ranking_position(db: Session, student_id: int, gym_id: int) -> Optional[int]:
    sub = (
        db.query(Student.id, StudentStats.total_xp)
        .join(User, User.id == Student.user_id)
        .outerjoin(StudentStats, StudentStats.student_id == Student.id)
        .filter(User.gym_id == gym_id)
        .order_by(
            func.coalesce(StudentStats.total_xp, 0).desc(),
            Student.id.asc(),
        )
        .all()
    )
    for idx, (sid, _) in enumerate(sub, start=1):
        if sid == student_id:
            return idx
    return None


def ranking_top(
    db: Session, gym_id: int, limit: int = 10
) -> list[dict[str, Any]]:
    rows = (
        db.query(Student, StudentStats, User)
        .join(User, User.id == Student.user_id)
        .outerjoin(StudentStats, StudentStats.student_id == Student.id)
        .filter(User.gym_id == gym_id)
        .order_by(
            func.coalesce(StudentStats.total_xp, 0).desc(),
            Student.id.asc(),
        )
        .limit(limit)
        .all()
    )
    out = []
    for pos, (st, stats, user) in enumerate(rows, start=1):
        xp = stats.total_xp if stats else 0
        lvl = stats.level if stats else 0
        out.append(
            {
                "position": pos,
                "student_id": st.id,
                "nome": st.nome,
                "email": user.email,
                "total_xp": xp,
                "level": lvl,
            }
        )
    return out
