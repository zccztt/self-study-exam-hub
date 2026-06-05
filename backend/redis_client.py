# -*- coding: utf-8 -*-
"""
Redis 客户端管理
"""

import redis
from redis.asyncio import Redis as AsyncRedis
from backend.config import settings
import json
from typing import Any, Optional


class RedisClient:
    """Redis 客户端类"""

    def __init__(self):
        self.client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            encoding='utf-8',
        )
        self.async_client = AsyncRedis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            encoding='utf-8',
        )

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            if expire:
                return self.client.setex(key, expire, serialized_value)
            return self.client.set(key, serialized_value)
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            value = self.client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            print(f"Redis get error: {e}")
            return None

    def delete(self, *keys: str) -> int:
        """删除缓存"""
        try:
            return self.client.delete(*keys)
        except Exception as e:
            print(f"Redis delete error: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self.client.exists(key) > 0

    async def aset(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """异步设置缓存"""
        try:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            if expire:
                return await self.async_client.setex(key, expire, serialized_value)
            return await self.async_client.set(key, serialized_value)
        except Exception as e:
            print(f"Redis aset error: {e}")
            return False

    async def aget(self, key: str) -> Optional[Any]:
        """异步获取缓存"""
        try:
            value = await self.async_client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            print(f"Redis aget error: {e}")
            return None


# 全局 Redis 客户端实例
redis_client = RedisClient()
