"""
Criptografia em repouso para credenciais de gateway (PayPal / Mercado Pago).

- Com ``PAYMENT_CREDENTIALS_FERNET_KEY`` definida, ``client_id``, ``client_secret``,
  ``access_token`` e ``refresh_token`` são gravados cifrados (Fernet).
- Sem a chave (ex.: testes locais), os valores permanecem em texto — compatível com dados legados.
- Quem tem a chave no ambiente consegue descriptografar em runtime (necessário para chamar as APIs).
  Quem só acessa o dump do banco não vê os segredos em claro.

Gere uma chave: ``python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"``
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

_ENV_KEY = "PAYMENT_CREDENTIALS_FERNET_KEY"


def fernet_key_configured() -> bool:
    return bool(os.getenv(_ENV_KEY, "").strip())


def _fernet() -> Fernet | None:
    raw = os.getenv(_ENV_KEY, "").strip()
    if not raw:
        return None
    return Fernet(raw.encode("ascii"))


def encrypt_credential(plain: str | None) -> str | None:
    if plain is None:
        return None
    s = plain.strip()
    if not s:
        return None
    f = _fernet()
    if f is None:
        return plain
    return f.encrypt(s.encode("utf-8")).decode("ascii")


def decrypt_credential(stored: str | None) -> str | None:
    if stored is None:
        return None
    s = stored.strip()
    if not s:
        return None
    f = _fernet()
    if f is None:
        return stored
    try:
        return f.decrypt(s.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        # Legado em texto claro ou chave rotacionada
        return stored


def mask_credential_suffix(stored: str | None, *, visible: int = 4) -> str | None:
    """Últimos caracteres do valor real (após decrypt), para UI/admin."""
    plain = decrypt_credential(stored)
    if not plain:
        return None
    if len(plain) <= visible:
        return "•" * min(len(plain), 8)
    return f"…{plain[-visible:]}"
