"""Armazenamento de sessões de refresh token: memória (padrão) ou Redis (REDIS_URL)."""

from __future__ import annotations

import os
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional


class RefreshSessionStore(ABC):
    @abstractmethod
    def put(self, token: str, ttl: timedelta) -> None:
        pass

    @abstractmethod
    def exists(self, token: str) -> bool:
        pass

    @abstractmethod
    def delete(self, token: str) -> None:
        pass


class MemoryRefreshSessionStore(RefreshSessionStore):
    def __init__(self) -> None:
        self._store: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def put(self, token: str, ttl: timedelta) -> None:
        expires_at = datetime.now(timezone.utc) + ttl
        with self._lock:
            self._store[token] = expires_at
            self._cleanup_locked()

    def exists(self, token: str) -> bool:
        now = datetime.now(timezone.utc)
        with self._lock:
            expires_at = self._store.get(token)
            if not expires_at:
                return False
            if expires_at <= now:
                self._store.pop(token, None)
                return False
            return True

    def delete(self, token: str) -> None:
        with self._lock:
            self._store.pop(token, None)

    def _cleanup_locked(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [k for k, v in self._store.items() if v <= now]
        for k in expired:
            self._store.pop(k, None)


class RedisRefreshSessionStore(RefreshSessionStore):
    def __init__(self, url: str) -> None:
        import redis

        self._r = redis.Redis.from_url(url, decode_responses=False)

    def put(self, token: str, ttl: timedelta) -> None:
        sec = max(1, int(ttl.total_seconds()))
        self._r.setex(f"refresh:{token}", sec, b"1")

    def exists(self, token: str) -> bool:
        return bool(self._r.exists(f"refresh:{token}"))

    def delete(self, token: str) -> None:
        self._r.delete(f"refresh:{token}")


_store: Optional[RefreshSessionStore] = None
_store_lock = threading.Lock()


def get_refresh_session_store() -> RefreshSessionStore:
    global _store
    with _store_lock:
        if _store is not None:
            return _store
        url = os.getenv("REDIS_URL", "").strip()
        if url:
            try:
                _store = RedisRefreshSessionStore(url)
            except Exception:
                _store = MemoryRefreshSessionStore()
        else:
            _store = MemoryRefreshSessionStore()
        return _store


def reset_refresh_session_store_for_tests() -> None:
    """Só para testes: força recriação após monkeypatch de REDIS_URL."""
    global _store
    with _store_lock:
        _store = None
