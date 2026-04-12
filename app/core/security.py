from passlib.context import CryptContext
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta, timezone
from typing import Optional
import os
from dotenv import load_dotenv
from app.core.session_store import get_refresh_session_store

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY não definida no ambiente")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


#  TOKEN BASE
def _create_token(data: dict, expires_delta: timedelta, token_type: str):
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    to_encode.update({"type": token_type, "iat": now, "exp": now + expires_delta})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _access_token_expire_delta() -> timedelta:
    """
    TTL do JWT de login (access). Padrão: 120 minutos (2 horas).
    Defina ACCESS_TOKEN_EXPIRE_MINUTES no .env (ex.: 60, 120). Entre 5 e 10080 (7 dias).
    """
    raw = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
    try:
        minutes = int(raw)
    except ValueError:
        minutes = 120
    minutes = max(5, min(minutes, 10080))
    return timedelta(minutes=minutes)


#  ACCESS TOKEN (login) — JWT com claim `exp`; após o prazo, decode falha.
def create_access_token(data: dict):
    return _create_token(data, _access_token_expire_delta(), "access")


#  REFRESH TOKEN (sessão em background)
def create_refresh_token(data: dict):
    ttl = timedelta(days=30)
    token = _create_token(data, ttl, "refresh")
    get_refresh_session_store().put(token, ttl)
    return token


def refresh_session_valid(token: str) -> bool:
    return get_refresh_session_store().exists(token)


def revoke_refresh_token(token: str) -> None:
    get_refresh_session_store().delete(token)


#  RESET TOKEN (senha)
def create_reset_token(email: str):
    return _create_token({"sub": email}, timedelta(minutes=30), "reset")


#  DECODE COM VALIDAÇÃO
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload

    except ExpiredSignatureError:
        return {"error": "expired"}

    except JWTError:
        return {"error": "invalid"}


def create_email_verification_token(user_id: int):
    return _create_token(
        {"user_id": user_id}, timedelta(hours=24), "email_verification"
    )


def create_mercadopago_oauth_state(
    gym_id: int, next_url: Optional[str] = None
) -> str:
    """JWT curto para o parâmetro `state` do OAuth Mercado Pago (CSRF + gym_id)."""
    payload: dict = {"gym_id": gym_id}
    if next_url is not None:
        if len(next_url) > 2048:
            raise ValueError("next_url excede o tamanho máximo")
        payload["next"] = next_url
    return _create_token(payload, timedelta(minutes=15), "mp_oauth")


def decode_mercadopago_oauth_state(token: str) -> dict:
    payload = decode_token(token)
    if payload.get("error"):
        raise ValueError("state inválido ou expirado")
    if payload.get("type") != "mp_oauth":
        raise ValueError("state inválido")
    try:
        gid = int(payload["gym_id"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError("state inválido") from e
    return {"gym_id": gid, "next": payload.get("next")}
