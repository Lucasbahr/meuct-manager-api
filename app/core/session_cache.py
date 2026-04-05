from datetime import datetime, timedelta, timezone
from threading import Lock


class SessionCache:
    def __init__(self):
        self._store: dict[str, datetime] = {}
        self._lock = Lock()

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


session_cache = SessionCache()

