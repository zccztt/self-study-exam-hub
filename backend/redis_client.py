# -*- coding: utf-8 -*-
"""Small Redis wrapper with graceful fallback when Redis is unavailable."""

import json
import logging
from typing import Any, Optional

import redis

from backend.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self) -> None:
        self.client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            encoding="utf-8",
            max_connections=50,
            socket_timeout=5,
            socket_connect_timeout=3,
            retry_on_timeout=True,
            health_check_interval=30,
        )

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        try:
            serialized = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            if expire:
                return bool(self.client.setex(key, expire, serialized))
            return bool(self.client.set(key, serialized))
        except Exception as exc:
            logger.warning("Redis SET failed for key=%s: %s", key, exc)
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
        except Exception as exc:
            logger.warning("Redis GET failed for key=%s: %s", key, exc)
            return None

    def delete(self, *keys: str) -> int:
        try:
            return int(self.client.delete(*keys))
        except Exception as exc:
            logger.warning("Redis DELETE failed for keys=%s: %s", keys, exc)
            return 0

    def exists(self, key: str) -> bool:
        try:
            return bool(self.client.exists(key))
        except Exception as exc:
            logger.warning("Redis EXISTS failed for key=%s: %s", key, exc)
            return False

    def increment_with_expiry(self, key: str, expire: int) -> Optional[int]:
        try:
            value = self.client.eval(
                "local value = redis.call('INCR', KEYS[1]); "
                "if value == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; "
                "return value",
                1,
                key,
                expire,
            )
            return int(value)
        except Exception as exc:
            logger.warning("Redis INCR failed for key=%s: %s", key, exc)
            return None


redis_client = RedisClient()
