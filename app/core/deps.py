from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from app.db.deps import get_db
from app.core.tenant import get_effective_gym_id
from app.core.roles import is_system_admin, is_academy_admin, is_staff

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_system_admin(user=Depends(get_current_user)):
    if not is_system_admin(user.get("role")):
        raise HTTPException(status_code=403, detail="Requer admin de sistema")
    return user


def require_academy_admin(user=Depends(get_current_user)):
    """Admin de sistema ou admin da academia (não professor)."""
    if not is_academy_admin(user.get("role")):
        raise HTTPException(
            status_code=403, detail="Requer admin da academia ou admin de sistema"
        )
    return user


def require_staff(user=Depends(get_current_user)):
    """Equipe: sistema, admin academia ou professor."""
    if not is_staff(user.get("role")):
        raise HTTPException(status_code=403, detail="Acesso restrito à equipe da academia")
    return user


def require_admin(user=Depends(get_current_user)):
    """Compatível com testes antigos: admin de academia ou sistema."""
    return require_academy_admin(user)


def require_gym_id(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> int:
    return get_effective_gym_id(db, user, request)
