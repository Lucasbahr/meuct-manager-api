from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TrainingCreate(BaseModel):
    student_id: int
    modality_id: int
    hours: Decimal = Field(gt=0, description="Horas de treino (positivo)")


class TrainingResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hours_trained: float
    total_xp: int
    level: int
    current_streak: int
    badges_unlocked: List[str]
    eligible_for_graduation: bool


class ModalityProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    modality_id: int
    modality_name: str
    graduation_id: int
    graduation_name: str
    level: int
    hours_trained: float
    required_hours: float
    progress_percent: float
    eligible: bool


class GamificationBadgeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    unlocked_at: Optional[str] = None


class GamificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_xp: int
    level: int
    current_streak: int
    best_streak: int
    training_sessions_count: int
    last_training_date: Optional[str] = None
    badges: List[GamificationBadgeItem]
    ranking_position: Optional[int] = None


class GraduateResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    new_graduation_id: int
    new_graduation_name: str
    new_level: int
    badges_unlocked: List[str]
    total_xp: int
    level: int


class RankingEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    student_id: int
    nome: str
    email: str
    total_xp: int
    level: int
