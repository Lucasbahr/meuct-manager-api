from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

FeedTipo = Literal["luta", "evento", "graduacao"]


class FeedItemCreate(BaseModel):
    tipo: FeedTipo
    titulo: str
    descricao: Optional[str] = None

    evento_data: Optional[date] = None
    local: Optional[str] = None

    modalidade: Optional[str] = None
    graduacao: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class FeedItemUpdate(BaseModel):
    tipo: Optional[FeedTipo] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    evento_data: Optional[date] = None
    local: Optional[str] = None
    modalidade: Optional[str] = None
    graduacao: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class FeedItemResponse(BaseModel):
    id: int
    created_by: int
    tipo: FeedTipo
    titulo: str
    descricao: Optional[str] = None

    evento_data: Optional[date] = None
    local: Optional[str] = None
    modalidade: Optional[str] = None
    graduacao: Optional[str] = None

    image_url: Optional[str] = None

    like_count: int
    comment_count: int
    liked_by_me: Optional[bool] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FeedLikeResponse(BaseModel):
    liked: bool
    like_count: int


class FeedCommentCreate(BaseModel):
    conteudo: str

    @field_validator("conteudo")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Conteudo não pode ser vazio")
        return v.strip()

    model_config = ConfigDict(extra="forbid")


class FeedCommentResponse(BaseModel):
    id: int
    user_id: int
    conteudo: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

