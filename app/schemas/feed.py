from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

FeedTipo = Literal["luta", "evento", "graduacao"]


class FeedItemCreate(BaseModel):
    tipo: FeedTipo = "evento"
    titulo: str
    descricao: Optional[str] = None

    evento_data: Optional[date] = None
    local: Optional[str] = None

    modalidade: Optional[str] = None
    graduacao: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("titulo")
    @classmethod
    def titulo_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Titulo não pode ser vazio")
        return v.strip()

    @field_validator("evento_data", mode="before")
    @classmethod
    def parse_evento_data(cls, v):
        if v in (None, ""):
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            raw = v.strip()
            # Flutter commonly sends ISO datetime from DateTime.toIso8601String()
            if "T" in raw:
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
                except ValueError:
                    pass
            try:
                return date.fromisoformat(raw)
            except ValueError:
                pass
            try:
                return datetime.strptime(raw, "%d/%m/%Y").date()
            except ValueError:
                pass
        raise ValueError("Data inválida. Use YYYY-MM-DD ou DD/MM/YYYY")


class FeedItemUpdate(BaseModel):
    tipo: Optional[FeedTipo] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    evento_data: Optional[date] = None
    local: Optional[str] = None
    modalidade: Optional[str] = None
    graduacao: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("titulo")
    @classmethod
    def titulo_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Titulo não pode ser vazio")
        return v.strip()

    @field_validator("evento_data", mode="before")
    @classmethod
    def parse_evento_data(cls, v):
        if v in (None, ""):
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            raw = v.strip()
            if "T" in raw:
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
                except ValueError:
                    pass
            try:
                return date.fromisoformat(raw)
            except ValueError:
                pass
            try:
                return datetime.strptime(raw, "%d/%m/%Y").date()
            except ValueError:
                pass
        raise ValueError("Data inválida. Use YYYY-MM-DD ou DD/MM/YYYY")


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

