"""Expõe `tenant_id` do JWT em `request.state` para inspeção em middlewares downstream."""

from jose import jwt, JWTError, ExpiredSignatureError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Preenche `request.state.tenant_id` a partir do claim `tenant_id` do Bearer JWT."""

    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = None
        if not SECRET_KEY or not ALGORITHM:
            return await call_next(request)

        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                if payload.get("type") != "access":
                    return await call_next(request)
                tid = payload.get("tenant_id")
                if tid is not None:
                    request.state.tenant_id = int(tid)
            except (ExpiredSignatureError, JWTError, TypeError, ValueError):
                pass

        return await call_next(request)
