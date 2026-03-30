from passlib.context import CryptContext
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from app.core.session_cache import session_cache

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


#  ACCESS TOKEN (login)
def create_access_token(data: dict):
    return _create_token(data, timedelta(hours=2), "access")


#  REFRESH TOKEN (sessão em background)
def create_refresh_token(data: dict):
    ttl = timedelta(days=30)
    token = _create_token(data, ttl, "refresh")
    session_cache.put(token, ttl)
    return token


def refresh_session_valid(token: str) -> bool:
    return session_cache.exists(token)


def revoke_refresh_token(token: str) -> None:
    session_cache.delete(token)


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
