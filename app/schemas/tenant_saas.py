"""Contratos HTTP para camada SaaS multi-tenant (white-label)."""

from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class TenantCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=128)
    slug: Optional[str] = Field(
        default=None,
        max_length=80,
        description="Opcional; gerado a partir do nome se omitido",
    )
    logo_url: Optional[HttpUrl] = None
    cor_primaria: Optional[str] = Field(default=None, max_length=16)
    cor_secundaria: Optional[str] = Field(default=None, max_length=16)
    cor_background: Optional[str] = Field(default=None, max_length=16)


class TenantPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    slug: str
    logo_url: Optional[str] = None
    cor_primaria: Optional[str] = None
    cor_secundaria: Optional[str] = None
    cor_background: Optional[str] = None
    ativo: bool


class TenantConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    permite_checkin: bool
    permite_agendamento: bool
    mostrar_ranking: bool
    mostrar_graduacao: bool
    cobrar_mensalidade: bool


class TenantPaymentConfigOut(BaseModel):
    """Somente dados públicos / flags; nunca access_token."""

    provider: str
    public_key: Optional[str] = None
    ativo: bool
    has_access_token_configured: bool


class GraduacaoSaaSOut(BaseModel):
    id: int
    modalidade_id: int
    nome: str
    ordem: int
    required_hours: Decimal


class ModalidadeSaaSOut(BaseModel):
    id: int
    nome: str


class TenantFullConfigOut(BaseModel):
    """Resposta agregada de GET /tenant/config (exemplo para Flutter / web)."""

    tenant: TenantPublicOut
    config: TenantConfigOut
    modalidades: List[ModalidadeSaaSOut]
    graduacoes: List[GraduacaoSaaSOut]
    payment_configs: List[TenantPaymentConfigOut]


class ModalidadeCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=128)


class GraduacaoCreate(BaseModel):
    modalidade_id: int = Field(ge=1)
    nome: str = Field(min_length=1, max_length=128)
    ordem: int = Field(ge=1, description="Mapeado para `level` em graduations")
    required_hours: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


PaymentProviderLiteral = Literal["mercadopago", "paypal", "mercado_pago"]
