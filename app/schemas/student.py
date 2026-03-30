from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Literal, Optional
import re

NivelCompeticao = Literal["amador", "profissional"]


class StudentCreate(BaseModel):
    nome: str
    email: str
    telefone: str
    modalidade: str
    graduacao: str
    e_atleta: bool = False
    cartel_mma: Optional[str] = None
    cartel_jiu: Optional[str] = None
    cartel_k1: Optional[str] = None
    nivel_competicao: Optional[NivelCompeticao] = None
    link_tapology: Optional[str] = None
    data_nascimento: Optional[date] = None
    ultima_luta_em: Optional[date] = None
    ultima_luta_modalidade: Optional[str] = None


class StudentUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    e_atleta: Optional[bool] = None
    cartel_mma: Optional[str] = None
    cartel_jiu: Optional[str] = None
    cartel_k1: Optional[str] = None
    nivel_competicao: Optional[NivelCompeticao] = None
    link_tapology: Optional[str] = None
    data_nascimento: Optional[date] = None
    ultima_luta_em: Optional[date] = None
    ultima_luta_modalidade: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("telefone")
    @classmethod
    def normalize_phone(cls, v):
        if v is None:
            return v

        digits = re.sub(r"\D", "", v)

        if len(digits) == 11:
            return f"+55{digits}"

        if re.match(r"^\+\d{10,15}$", v):
            return v

        raise ValueError("Telefone inválido")


class StudentAdminUpdate(StudentUpdate):
    modalidade: Optional[str] = None
    graduacao: Optional[str] = None
    status: Optional[str] = None
    tempo_de_treino: Optional[int] = None


class StudentResponse(BaseModel):
    id: int
    nome: Optional[str]
    email: Optional[str]
    telefone: Optional[str]
    endereco: Optional[str]
    modalidade: Optional[str]
    graduacao: Optional[str]
    tempo_de_treino: Optional[int]
    status: Optional[str]
    e_atleta: bool
    cartel_mma: Optional[str]
    cartel_jiu: Optional[str]
    cartel_k1: Optional[str]
    nivel_competicao: Optional[str]
    link_tapology: Optional[str]
    data_nascimento: Optional[date]
    ultima_luta_em: Optional[date]
    ultima_luta_modalidade: Optional[str]
    foto_url: Optional[str]

    model_config = ConfigDict(from_attributes=True)
