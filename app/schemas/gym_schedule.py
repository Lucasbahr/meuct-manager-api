"""Schemas para aulas da academia e grade horária semanal."""

from datetime import time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


WEEKDAY_LABELS_PT = (
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
)


class GymClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    modality_id: Optional[int] = Field(default=None, ge=1)
    instructor_name: Optional[str] = Field(default=None, max_length=255)
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    sort_order: int = Field(default=0, ge=0, le=9999)
    is_active: bool = True


class GymClassUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    modality_id: Optional[int] = Field(default=None, ge=1)
    instructor_name: Optional[str] = Field(default=None, max_length=255)
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    sort_order: Optional[int] = Field(default=None, ge=0, le=9999)
    is_active: Optional[bool] = None


class GymClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gym_id: int
    name: str
    description: Optional[str] = None
    modality_id: Optional[int] = None
    instructor_name: Optional[str] = None
    duration_minutes: Optional[int] = None
    sort_order: int = 0
    is_active: bool = True


class GymScheduleSlotCreate(BaseModel):
    gym_class_id: int = Field(ge=1)
    weekday: int = Field(ge=0, le=6, description="0=segunda … 6=domingo (datetime.weekday)")
    start_time: time
    end_time: time
    room: Optional[str] = Field(default=None, max_length=128)
    notes: Optional[str] = Field(default=None, max_length=512)
    is_active: bool = True

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time deve ser posterior a start_time")
        return self


class GymScheduleSlotUpdate(BaseModel):
    gym_class_id: Optional[int] = Field(default=None, ge=1)
    weekday: Optional[int] = Field(default=None, ge=0, le=6)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    room: Optional[str] = Field(default=None, max_length=128)
    notes: Optional[str] = Field(default=None, max_length=512)
    is_active: Optional[bool] = None


class GymScheduleSlotOut(BaseModel):
    """Horário na grade + resumo da aula (para o app)."""

    id: int
    gym_id: int
    weekday: int
    weekday_label: str
    start_time: str
    end_time: str
    room: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    class_info: GymClassOut


class GymScheduleGroupedOut(BaseModel):
    """Opcional: mesma grade agrupada por dia (útil no Flutter)."""

    weekday: int
    weekday_label: str
    slots: List[GymScheduleSlotOut]
