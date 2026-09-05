# -*- coding: utf-8 -*-
"""Small fixed-window rate limiter with Redis and local fallback."""

from threading import Lock
from time import time
from typing import Dict, Tuple

from fastapi import HTTPException, Request, status

from backend.redis_client import RedisClient, redis_client


class RateLimiter:
    def __init__(self, redis: RedisClient = redis_client) -> None:
        self.redis = redis
        self._local: Dict[str, Tuple[float, int]] = {}
        self._lock = Lock()

    def check(self, scope: str, identifier: str, limit: int, window_seconds: int = 60) -> None:
        safe_limit = max(1, int(limit))
        safe_window = max(1, int(window_seconds))
        window = int(time() // safe_window)
        key = self._key(scope, identifier, window)
        count = self.redis.increment_with_expiry(key, safe_window + 1)
        if count is None:
            count = self._increment_local(key, safe_window)
        if count > safe_limit:
            retry_after = safe_window - int(time() % safe_window)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试。",
                headers={"Retry-After": str(max(1, retry_after))},
            )

    def reset(self, scope: str, identifier: str, window_seconds: int = 60) -> None:
        safe_window = max(1, int(window_seconds))
        current_window = int(time() // safe_window)
        keys = [self._key(scope, identifier, window) for window in range(current_window - 1, current_window + 2)]
        with self._lock:
            for key in keys:
                self._local.pop(key, None)
        self.redis.delete(*keys)

    @staticmethod
    def _key(scope: str, identifier: str, window: int) -> str:
        return f"rate_limit:{scope}:{identifier}:{window}"

    def _increment_local(self, key: str, window_seconds: int) -> int:
        now = time()
        with self._lock:
            started_at, count = self._local.get(key, (now, 0))
            if now - started_at >= window_seconds:
                started_at, count = now, 0
            count += 1
            self._local[key] = (started_at, count)
            if len(self._local) > 5000:
                cutoff = now - window_seconds * 2
                self._local = {
                    item_key: value
                    for item_key, value in self._local.items()
                    if value[0] >= cutoff
                }
            return count


def client_identifier(request: Request) -> str:
    return request.client.host if request.client else "unknown"


rate_limiter = RateLimiter()
