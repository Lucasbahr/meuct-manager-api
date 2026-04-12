from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.models.gym import Gym
from app.models.user import User
from app.core.roles import is_academy_admin, is_system_admin, normalize_role


def _parse_gym_id(raw: str | None) -> int | None:
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="gym_id inválido")


def _header_gym_id(request: Request) -> int | None:
    """Prefer X-Gym-Id; aceita X-Academia-Id (legado)."""
    h = request.headers.get("X-Gym-Id") or request.headers.get("X-Academia-Id")
    return _parse_gym_id(h)


def get_effective_gym_id(
    db: Session,
    token_user: dict,
    request: Request,
) -> int:
    """
    Tenant em rotas autenticadas:
    - ADMIN_SISTEMA: X-Gym-Id ou X-Academia-Id (legado), ou gym_id do usuário se existir.
    - Demais perfis: gym do usuário; header só se igual ao próprio.
    """
    u = db.query(User).filter(User.id == token_user["user_id"]).first()
    if not u:
        raise HTTPException(status_code=401, detail="User not found")

    role = normalize_role(u.role)
    header_id = _header_gym_id(request)

    if is_system_admin(role):
        if header_id is not None:
            if db.query(Gym).filter(Gym.id == header_id).first() is None:
                raise HTTPException(status_code=400, detail="Gym não encontrado")
            return header_id
        if u.gym_id is not None:
            return u.gym_id
        raise HTTPException(
            status_code=400,
            detail="Admin de sistema: informe o header X-Gym-Id com o id do gym",
        )

    if u.gym_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário sem gym associado; contate o suporte",
        )

    if header_id is not None:
        if db.query(Gym).filter(Gym.id == header_id).first() is None:
            raise HTTPException(status_code=400, detail="Gym não encontrado")
        if header_id != u.gym_id:
            raise HTTPException(
                status_code=403,
                detail="Você só pode atuar no seu próprio gym",
            )
        return header_id

    return u.gym_id


def get_feed_gym_id(
    db: Session,
    request: Request,
    token_user: dict | None,
) -> int:
    """
    Feed público: ?gym_id= ou ?academia_id= (legado) ou X-Gym-Id / X-Academia-Id.
    Autenticado: mesma regra que get_effective_gym_id.
    """
    if token_user:
        return get_effective_gym_id(db, token_user, request)
    q_gym = request.query_params.get("gym_id")
    q_legacy = request.query_params.get("academia_id")
    raw = q_gym if q_gym not in (None, "") else q_legacy
    header = _header_gym_id(request)
    gid = _parse_gym_id(raw) if raw not in (None, "") else header
    if gid is None:
        raise HTTPException(
            status_code=400,
            detail="Informe gym_id na query ou header X-Gym-Id (ou legado academia_id / X-Academia-Id)",
        )
    if db.query(Gym).filter(Gym.id == gid).first() is None:
        raise HTTPException(status_code=400, detail="Gym não encontrado")
    return gid
