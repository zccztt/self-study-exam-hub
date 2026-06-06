# -*- coding: utf-8 -*-
"""Small Redis wrapper with graceful fallback when Redis is unavailable."""

import json
from typing import Any, Optional

import redis

from backend.config import settings


class RedisClient:
    def __init__(self) -> None:
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True, encoding="utf-8")

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        try:
            serialized = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            if expire:
                return bool(self.client.setex(key, expire, serialized))
            return bool(self.client.set(key, serialized))
        except Exception:
            return False

    def get(self, key: str) -> Optional[Any]:
        try:
            value = self.client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception:
            return None

    def delete(self, *keys: str) -> int:
        try:
            return int(self.client.delete(*keys))
        except Exception:
            return 0

    def exists(self, key: str) -> bool:
        try:
            return bool(self.client.exists(key))
        except Exception:
            return False


redis_client = RedisClient()
