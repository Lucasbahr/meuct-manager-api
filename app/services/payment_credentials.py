"""Descriptografia pontual das credenciais da academia para chamadas aos provedores."""

from __future__ import annotations

from dataclasses import dataclass

from app.core import payment_credentials_crypto as pcc
from app.models.marketplace import GymPaymentSettings


@dataclass
class ProviderCredentials:
    """Valores em claro só na memória do processo durante a requisição."""

    client_id: str | None
    client_secret: str | None
    access_token: str | None
    refresh_token: str | None


def decrypt_row(row: GymPaymentSettings) -> ProviderCredentials:
    return ProviderCredentials(
        client_id=pcc.decrypt_credential(row.client_id),
        client_secret=pcc.decrypt_credential(row.client_secret),
        access_token=pcc.decrypt_credential(row.access_token),
        refresh_token=pcc.decrypt_credential(row.refresh_token),
    )
