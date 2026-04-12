from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Literal, Optional, List
import re

NivelCompeticao = Literal["amador", "profissional"]


class StudentModalityItem(BaseModel):
    id: int
    modality_id: int
    modality_name: str
    graduation_id: int
    graduation_name: str
    graduation_level: int
    hours_trained: Decimal

    model_config = ConfigDict(from_attributes=True)


class ProfessorModalityItem(BaseModel):
    """Modalidade em que o aluno atua como professor."""

    id: int
    modality_id: int
    modality_name: str

    model_config = ConfigDict(from_attributes=True)


class StudentModalityCreateBody(BaseModel):
    student_id: int
    modality_id: int
    graduation_id: int
    hours_trained: Optional[Decimal] = None


class StudentCreate(BaseModel):
    nome: str
    email: str
    telefone: str
    modality_id: Optional[int] = None
    graduation_id: Optional[int] = None
    e_atleta: bool = False
    e_professor: bool = False
    cartel_mma: Optional[str] = None
    cartel_jiu: Optional[str] = None
    cartel_k1: Optional[str] = None
    nivel_competicao: Optional[NivelCompeticao] = None
    link_tapology: Optional[str] = None
    data_nascimento: Optional[date] = None
    ultima_luta_em: Optional[date] = None
    ultima_luta_modalidade: Optional[str] = None

    @model_validator(mode="after")
    def modality_pair(self):
        a, b = self.modality_id, self.graduation_id
        if (a is None) ^ (b is None):
            raise ValueError("Informe modality_id e graduation_id juntos, ou nenhum")
        return self


class StudentUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    e_atleta: Optional[bool] = None
    e_professor: Optional[bool] = None
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
    status: Optional[str] = None
    tempo_de_treino: Optional[int] = None
    professor_modality_ids: Optional[List[int]] = None
    modality_id: Optional[int] = None
    graduation_id: Optional[int] = None

    @model_validator(mode="after")
    def modality_graduation_pair(self):
        a, b = self.modality_id, self.graduation_id
        if (a is None) ^ (b is None):
            raise ValueError("Informe modality_id e graduation_id juntos, ou nenhum")
        return self


class StudentResponse(BaseModel):
    id: int
    nome: Optional[str]
    email: Optional[str]
    telefone: Optional[str]
    endereco: Optional[str]
    tempo_de_treino: Optional[int]
    status: Optional[str]
    e_atleta: bool
    e_professor: bool
    cartel_mma: Optional[str]
    cartel_jiu: Optional[str]
    cartel_k1: Optional[str]
    nivel_competicao: Optional[str]
    link_tapology: Optional[str]
    data_nascimento: Optional[date]
    ultima_luta_em: Optional[date]
    ultima_luta_modalidade: Optional[str]
    foto_url: Optional[str]
    foto_atleta_url: Optional[str]
    modalities: List[StudentModalityItem] = []
    professor_modalities: List[ProfessorModalityItem] = []
    # Compatível com apps que ainda leem `modalidade` / `graduacao` (primeira inscrição).
    modalidade: Optional[str] = None
    graduacao: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
