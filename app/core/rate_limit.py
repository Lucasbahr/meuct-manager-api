"""Rate limit simples por IP (login/registro), sem dependências extras."""

from __future__ import annotations

import os
import threading
import time
from typing import Dict, List, Tuple

_lock = threading.Lock()
_buckets: Dict[str, List[float]] = {}


def rate_limit_enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _prune_key(key: str, window: float, now: float) -> None:
    arr = _buckets.get(key, [])
    arr = [t for t in arr if now - t < window]
    if arr:
        _buckets[key] = arr
    else:
        _buckets.pop(key, None)


def check_rate_limit(
    client_ip: str,
    *,
    bucket_key: str,
    max_calls: int,
    window_seconds: int,
) -> Tuple[bool, int]:
    """
    Retorna (permitido, retry_after_segundos).
    retry_after_segundos só é >0 quando permitido é False.
    """
    if not rate_limit_enabled():
        return True, 0

    now = time.time()
    key = f"{bucket_key}:{client_ip}"
    window = float(window_seconds)

    with _lock:
        _prune_key(key, window, now)
        arr = _buckets.get(key, [])
        if len(arr) >= max_calls:
            oldest = min(arr)
            retry_after = int(window - (now - oldest)) + 1
            return False, max(1, retry_after)

        arr.append(now)
        _buckets[key] = arr

        if len(_buckets) > 50_000:
            cutoff = now - 3600
            dead = [k for k, ts in _buckets.items() if not ts or max(ts) < cutoff]
            for k in dead[:5_000]:
                _buckets.pop(k, None)

        return True, 0


def client_ip_from_request(request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
