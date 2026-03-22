from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
import re


class StudentCreate(BaseModel):
    nome: str
    email: str
    telefone: str
    modalidade: str
    graduacao: str


class StudentUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None

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

    model_config = ConfigDict(from_attributes=True)
